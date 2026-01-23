/**
 * Knowledge Graph D3.js Visualization
 * MCP-based client that fetches data from the MCP server
 */

console.log('[graph.js] Module loading...');

import { initMCPClient, readGraph, searchNodes } from './mcp-client.js';

console.log('[graph.js] MCP client functions imported:', { initMCPClient, readGraph, searchNodes });

// Global variables
const width = window.innerWidth;
const height = window.innerHeight;
let graphData = { nodes: [], links: [] };
let searchIndex = [];
let simulation;
let svg, container, zoom;
let autoFitTimeout = null;
let currentHighlightedNode = null;

// Check for test mode (disables animations for faster testing)
const urlParams = new URLSearchParams(window.location.search);
const testMode = urlParams.get('testMode') === 'true';

// Color mapping for node groups
const colorMap = {
    person: "#e74c3c",
    project: "#2ecc71",
    technology: "#3498db",
    development: "#f39c12",
    strategy: "#9b59b6",
    debug: "#e91e63"
};

function getNodeColor(group) {
    return colorMap[group] || "#95a5a6";
}

// Initialize the visualization
function initializeVisualization() {
    svg = d3.select("#graph")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", `0 0 ${width} ${height}`)
        .style("width", "100vw")
        .style("height", "100vh");

    zoom = d3.zoom()
        .scaleExtent([0.1, 10])
        .on("zoom", function(event) {
            container.attr("transform", event.transform);
        })
        .on("start", function(event) {
            // Cancel auto-fit when user manually zooms or pans
            if (event.sourceEvent) {
                cancelAutoFit();
            }
        });

    svg.call(zoom);
    container = svg.append("g");

    // Hide context menu on clicks elsewhere
    svg.on('click', function(event) {
        if (event.target === this || event.target.tagName === 'svg') {
            hideContextMenu();
        }
    });

// Initialize force simulation
    simulation = d3.forceSimulation()
        .force("link", d3.forceLink().id(d => d.id).distance(150).strength(0.8))
        .force("charge", d3.forceManyBody().strength(-800))  // Stronger repulsion
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(d => Math.sqrt(d.degree) * 4 + 20).strength(0.9))
        .force("x", d3.forceX(width / 2).strength(0.1))  // Gentle centering
        .force("y", d3.forceY(height / 2).strength(0.1))
        .alphaDecay(0.02)  // Slower cooling
        .velocityDecay(0.4);  // More damping
}

// Convert backend data format to D3 graph format
function convertDataToGraph(data) {
    // Convert entities to nodes
    const nodes = (data.entities || []).map(entity => ({
        id: entity.name,
        group: entity.entityType || 'unknown',
        type: entity.entityType || 'unknown',
        observations: entity.observations || []
    }));

    // Convert relations to links
    const links = (data.relations || []).map(relation => ({
        source: relation.from_entity,
        target: relation.to,
        relation: relation.relationType || 'relates_to'
    }));

    return {
        nodes,
        links,
        stats: {
            nodeCount: nodes.length,
            linkCount: links.length
        }
    };
}

// Load knowledge graph data using REST API
async function loadKnowledgeGraph() {
    const loadingEl = document.getElementById('loading');
    loadingEl.style.display = 'flex';

    const startTime = performance.now();

    console.log('Starting to load knowledge graph...');

    try {
        // Initialize MCP client if needed
        console.log('Initializing MCP client...');
        await initMCPClient();

        // Fetch graph data from MCP server
        console.log('Reading graph via MCP...');
        const data = await readGraph('default');
        console.log('Data loaded:', data.entities?.length || 0, 'entities,', data.relations?.length || 0, 'relations');
        const loadTime = Math.round(performance.now() - startTime);

        // Initialize visualization if not done yet
        if (!svg) {
            console.log('Initializing visualization...');
            initializeVisualization();
        }

        // Convert data format to visualization format
        const graphData = convertDataToGraph(data);
        console.log('Converted to graph format:', graphData.nodes.length, 'nodes,', graphData.links.length, 'links');

        // Update the visualization
        updateKnowledgeGraph(graphData.nodes, graphData.links);

        // Update stats
        document.getElementById('loadTime').textContent = `Load: ${loadTime}ms`;

        console.log('Knowledge graph loaded:', graphData.stats);

    } catch (error) {
        console.error('Failed to load knowledge graph:', error);
        showError(`Failed to load knowledge graph: ${error.message}`);
    } finally {
        loadingEl.style.display = 'none';
    }
}

// Update the graph visualization
function updateKnowledgeGraph(nodes, links) {
    console.log('Raw data from server:', { nodes: nodes.slice(0, 2), links: links.slice(0, 2) });

    // Store the data and give nodes initial positions
    // Create completely plain objects that D3 can modify freely
    graphData.nodes = nodes.map((d, i) => {
        // Create a completely plain object
        const node = Object.create(null);
        node.id = d.id;
        node.group = d.group;
        node.type = d.type;
        node.observations = Array.isArray(d.observations) ? [...d.observations] : [];
        node.x = width/2 + (Math.random() - 0.5) * 200;
        node.y = height/2 + (Math.random() - 0.5) * 200;
        node.vx = (Math.random() - 0.5) * 50;
        node.vy = (Math.random() - 0.5) * 50;
        node.index = i;

        // Test if properties are writable
        try {
            node.x = node.x + 1;
            node.y = node.y + 1;
            node.vx = node.vx;
            node.vy = node.vy;
        } catch (e) {
            console.error('Node property not writable:', e, node);
        }

        return node;
    });

    graphData.links = links.map(d => {
        const link = Object.create(null);
        link.source = d.source;
        link.target = d.target;
        link.relation = d.relation;
        return link;
    });

    console.log('Processed nodes sample:', graphData.nodes.slice(0, 2));
    console.log('Processed links sample:', graphData.links.slice(0, 2));
    console.log(`Updating graph with ${nodes.length} nodes and ${links.length} links`);

    // Calculate node degrees for sizing
    const degreeMap = {};
    graphData.nodes.forEach(n => degreeMap[n.id] = 0);
    graphData.links.forEach(l => {
        degreeMap[l.source]++;
        degreeMap[l.target]++;
    });
    graphData.nodes.forEach(n => n.degree = degreeMap[n.id] || 1);

    // Update links
    const link = container.selectAll(".link")
        .data(graphData.links);

    link.exit().remove();

    const linkEnter = link.enter().append("line")
        .attr("class", "link")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .attr("stroke-width", 2);

    const linkUpdate = linkEnter.merge(link);

    // Update nodes
    const node = container.selectAll(".node")
        .data(graphData.nodes);

    node.exit().remove();

    const nodeEnter = node.enter().append("circle")
        .attr("class", "node")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5);

    const nodeUpdate = nodeEnter.merge(node)
        .attr("r", d => Math.sqrt(d.degree) * 4 + 8)
        .attr("fill", d => getNodeColor(d.group));

    // Add interactions
    nodeUpdate.call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Add context menu on right-click
    nodeUpdate.on('contextmenu', function(event, d) {
        event.preventDefault();
        event.stopPropagation();
        showContextMenu(event, d);
    });

    // Fallback: Ctrl+Click or Alt+Click for browsers that don't support context menu (like VS Code Simple Browser)
    nodeUpdate.on('click', function(event, d) {
        // Cancel auto-fit on any click
        cancelAutoFit();

        if (event.ctrlKey || event.altKey || event.metaKey) {
            event.stopPropagation();
            showContextMenu(event, d);
        } else {
            event.stopPropagation();
            showEntityDetails(d.id);
        }
    });

    // Update labels
    const label = container.selectAll(".label")
        .data(graphData.nodes);

    label.exit().remove();

    const labelEnter = label.enter().append("text")
        .attr("class", "label")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .style("font", "12px sans-serif")
        .style("fill", "#333")
        .style("pointer-events", "none");

    labelEnter.merge(label)
        .each(function(d) {
            const text = d3.select(this);
            text.selectAll("*").remove();

            const words = d.id.split(" ");
            if (words.length > 2) {
                text.append("tspan")
                    .attr("x", 0)
                    .attr("dy", "-0.3em")
                    .text(words.slice(0, 2).join(" "));
                text.append("tspan")
                    .attr("x", 0)
                    .attr("dy", "1.2em")
                    .text(words.slice(2).join(" "));
            } else {
                text.text(d.id);
            }
        });

    // Update simulation with proper restart and error handling
    try {
        console.log('Available node IDs:', graphData.nodes.map(n => n.id));
        console.log('Link source/target IDs:', graphData.links.map(l => ({ source: l.source, target: l.target })));

        // Check for missing nodes referenced in links
        const nodeIds = new Set(graphData.nodes.map(n => n.id));
        const missingNodes = new Set();

        graphData.links.forEach(link => {
            if (!nodeIds.has(link.source)) {
                missingNodes.add(link.source);
            }
            if (!nodeIds.has(link.target)) {
                missingNodes.add(link.target);
            }
        });

        if (missingNodes.size > 0) {
            console.error('Missing nodes referenced in links:', Array.from(missingNodes));
            // Filter out links that reference missing nodes
            graphData.links = graphData.links.filter(link =>
                nodeIds.has(link.source) && nodeIds.has(link.target)
            );
            console.log('Filtered links to remove references to missing nodes');
            console.log('Remaining links:', graphData.links.length);
        }

        console.log('Setting simulation nodes...');
        simulation.nodes(graphData.nodes);

        console.log('Setting simulation links...');
        simulation.force("link").links(graphData.links);

        console.log('Force simulation restarting with alpha 1.0');

        // Force restart with very high alpha for strong initial layout
        // In test mode, skip animation for faster testing
        if (testMode) {
            simulation.alpha(1.0).restart();
            // Settle immediately in test mode
            setTimeout(() => {
                simulation.alphaTarget(0);
            }, 100);
        } else {
            simulation.alpha(1.0).alphaTarget(0.3).restart();
            // Remove alpha target after longer settling period
            setTimeout(() => {
                console.log('Removing alphaTarget, allowing natural cooling');
                try {
                    simulation.alphaTarget(0);
                } catch (e) {
                    console.error('Error removing alphaTarget:', e);
                }
            }, 5000);
        }

    } catch (e) {
        console.error('Error in simulation setup:', e);
        console.error('Stack trace:', e.stack);

        // Try a simpler approach
        console.log('Attempting simple simulation restart...');
        try {
            simulation.stop();
            simulation.nodes([]);
            simulation.force("link").links([]);

            setTimeout(() => {
                simulation.nodes(graphData.nodes);
                simulation.force("link").links(graphData.links);
                simulation.alpha(0.3).restart();
            }, 100);
        } catch (e2) {
            console.error('Even simple restart failed:', e2);
        }
    }

    // Create search index
    createSearchIndex(graphData.nodes);

    simulation.on("tick", function() {
        linkUpdate
            .attr("x1", d => d.source.x || 0)
            .attr("y1", d => d.source.y || 0)
            .attr("x2", d => d.target.x || 0)
            .attr("y2", d => d.target.y || 0);

        nodeUpdate
            .attr("cx", d => d.x || 0)
            .attr("cy", d => d.y || 0);

        container.selectAll(".label")
            .attr("x", d => d.x || 0)
            .attr("y", d => d.y || 0)
            .selectAll("tspan")
            .attr("x", function() {
                const datum = d3.select(this.parentNode).datum();
                return datum.x || 0;
            });
    });

    // Don't call restart again here since we already did above
    // simulation.alpha(1).restart();

    // Update stats
    document.getElementById('nodeCount').textContent = `Entities: ${graphData.nodes.length}`;
    document.getElementById('linkCount').textContent = `Relations: ${graphData.links.length}`;

    // Auto-fit after simulation has settled longer, but cancel if user interacts
    if (autoFitTimeout) clearTimeout(autoFitTimeout);
    autoFitTimeout = setTimeout(() => {
        // Only fit if user hasn't interacted
        if (autoFitTimeout) {
            fitToScreen();
            autoFitTimeout = null;
        }
    }, 6000);
}

// Search functionality
function createSearchIndex(nodes) {
    searchIndex = [];
    nodes.forEach(node => {
        // Add entity name
        searchIndex.push({
            type: 'name',
            entity: node.id,
            content: node.id,
            entityType: node.type
        });

        // Add observations
        if (node.observations) {
            node.observations.forEach((obs, index) => {
                searchIndex.push({
                    type: 'observation',
                    entity: node.id,
                    content: obs,
                    entityType: node.type,
                    observationIndex: index
                });
            });
        }
    });
}

async function performServerSearch(query) {
    if (!query.trim() || query.length < 2) return [];

    try {
        // Initialize MCP client if needed
        await initMCPClient();

        // Search via MCP
        const data = await searchNodes(query);

        // Backend already returns deduplicated entities with all observations
        // Just pass through the structure
        return data.entities || [];
    } catch (error) {
        console.error('Search error:', error);
        return [];
    }
}

function highlightText(text, query) {
    if (!query.trim()) return text;

    const terms = query.toLowerCase().split(/\s+/);
    let highlighted = text;

    terms.forEach(term => {
        const regex = new RegExp(`(${term})`, 'gi');
        highlighted = highlighted.replace(regex, '<span class="highlight">$1</span>');
    });

    return highlighted;
}

async function showSearchResults(query) {
    const container = document.getElementById('searchResults');

    if (!query.trim()) {
        container.innerHTML = '';
        return;
    }

    // Show loading
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">Searching...</div>';

    const results = await performServerSearch(query);

    if (results.length === 0) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">No results found</div>';
        return;
    }

    // Display consolidated results with collapsible observations
    // Use data attributes instead of inline onclick to avoid XSS and string escaping issues
    container.innerHTML = results.map(entity => {
        const safeId = entity.name.replace(/[^a-zA-Z0-9]/g, '_');
        const observationsHtml = entity.observations && entity.observations.length > 0 ? `
            <div class="observations-toggle" data-entity-name="${entity.name}">
                <span class="toggle-icon">▶</span>
                <span>${entity.observations.length} observation${entity.observations.length > 1 ? 's' : ''}${
                    entity.observationMatches > 0 ? ` (${entity.observationMatches} match${entity.observationMatches > 1 ? 'es' : ''})` : ''
                }</span>
            </div>
            <div class="observations-list" id="obs-${safeId}" style="display: none;">
                ${entity.observations.map((obs, index) => {
                    const snippet = obs.length > 120 ? obs.substring(0, 120) + '...' : obs;
                    return `
                        <div class="observation-item" data-entity-name="${entity.name}" data-obs-index="${index}">
                            ${highlightText(snippet, query)}
                        </div>
                    `;
                }).join('')}
            </div>
        ` : '';

        return `
            <div class="search-result" data-entity-name="${entity.name}">
                <div class="result-title">
                    ${highlightText(entity.name, query)}
                    <span class="result-type-inline">(${entity.entityType})</span>
                </div>
                ${observationsHtml}
            </div>
        `;
    }).join('');

    // Attach event listeners using delegation
    container.querySelectorAll('.search-result').forEach(result => {
        const entityName = result.dataset.entityName;
        result.addEventListener('click', (e) => {
            // Don't trigger if clicking on observations toggle or observation item
            if (e.target.closest('.observations-toggle') || e.target.closest('.observation-item')) {
                return;
            }
            showEntityDetails(entityName);
        });
    });

    container.querySelectorAll('.observations-toggle').forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const entityName = toggle.dataset.entityName;
            const safeId = entityName.replace(/[^a-zA-Z0-9]/g, '_');
            const observationsList = document.getElementById(`obs-${safeId}`);
            const toggleIcon = toggle.querySelector('.toggle-icon');

            if (observationsList.style.display === 'none') {
                observationsList.style.display = 'block';
                toggleIcon.textContent = '▼';
            } else {
                observationsList.style.display = 'none';
                toggleIcon.textContent = '▶';
            }
        });
    });

    container.querySelectorAll('.observation-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const entityName = item.dataset.entityName;
            const obsIndex = parseInt(item.dataset.obsIndex, 10);
            showEntityDetails(entityName, obsIndex);
        });
    });
}

function showEntityDetails(entityName, highlightObservationIndex = null) {
    const entity = graphData.nodes.find(n => n.id === entityName);
    if (!entity) return;

    const panel = document.getElementById('detailPanel');
    const title = document.getElementById('detailTitle');
    const content = document.querySelector('.detail-content');

    title.textContent = entity.id;

    let html = `
        <div class="detail-section">
            <button onclick="zoomToNodeByName('${entity.id.replace(/'/g, "\\'")}')"
                    style="width: 100%; padding: 10px; margin-bottom: 15px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                🔍 Zoom to This Node
            </button>
        </div>
        <div class="detail-section">
            <h4>Type</h4>
            <div style="color: ${getNodeColor(entity.group)}; font-weight: bold;">${entity.type}</div>
        </div>
    `;

    if (entity.observations && entity.observations.length > 0) {
        html += `
            <div class="detail-section">
                <h4>Observations (${entity.observations.length})</h4>
                ${entity.observations.map((obs, index) => `
                    <div class="observation-item ${highlightObservationIndex === index ? 'highlighted' : ''}">
                        ${obs}
                    </div>
                `).join('')}
            </div>
        `;
    }

    // Show connections
    const connections = graphData.links.filter(l =>
        l.source.id === entityName || l.target.id === entityName
    );

    if (connections.length > 0) {
        html += `
            <div class="detail-section">
                <h4>Connections (${connections.length})</h4>
                ${connections.map(conn => {
                    const isSource = conn.source.id === entityName;
                    const otherEntity = isSource ? conn.target.id : conn.source.id;
                    const relation = isSource ? conn.relation : `← ${conn.relation}`;

                    return `
                        <div class="connection-item" onclick="showEntityDetails('${otherEntity}')">
                            <strong>${relation}</strong> ${otherEntity}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    content.innerHTML = html;
    panel.style.display = 'flex';

    // Highlight the node in the graph
    highlightNode(entityName);
}

function highlightNode(entityName) {
    currentHighlightedNode = entityName;
    svg.selectAll('.node')
        .transition()
        .duration(300)
        .attr('stroke', d => d.id === entityName ? '#ff6b35' : '#fff')
        .attr('stroke-width', d => d.id === entityName ? 4 : 1.5)
        .attr('r', d => {
            const baseRadius = Math.sqrt(d.degree) * 4 + 8;
            return d.id === entityName ? baseRadius * 1.3 : baseRadius;
        });
}

function clearHighlight() {
    currentHighlightedNode = null;
    svg.selectAll('.node')
        .transition()
        .duration(300)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .attr('r', d => Math.sqrt(d.degree) * 4 + 8);
}

function showError(message) {
    const errorEl = document.createElement('div');
    errorEl.className = 'error';
    errorEl.textContent = message;
    document.body.appendChild(errorEl);

    setTimeout(() => {
        document.body.removeChild(errorEl);
    }, 5000);
}

// UI Controls
function toggleSearch() {
    const panel = document.getElementById('searchPanel');
    const btn = document.getElementById('searchBtn');

    if (panel.style.display === 'none') {
        panel.style.display = 'flex';
        btn.textContent = 'Hide Search';
        document.getElementById('searchInput').focus();
    } else {
        panel.style.display = 'none';
        btn.textContent = 'Search';
    }
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.getElementById('searchResults').innerHTML = '';
}

function toggleObservations(entityName) {
    const safeId = entityName.replace(/[^a-zA-Z0-9]/g, '_');
    const observationsList = document.getElementById(`obs-${safeId}`);
    const toggleIcon = event.currentTarget.querySelector('.toggle-icon');

    if (observationsList.style.display === 'none') {
        observationsList.style.display = 'block';
        toggleIcon.textContent = '▲';
    } else {
        observationsList.style.display = 'none';
        toggleIcon.textContent = '▼';
    }

    // Prevent click from bubbling to parent search-result
    event.stopPropagation();
}

function closeDetail() {
    document.getElementById('detailPanel').style.display = 'none';
    clearHighlight();
}

function cancelAutoFit() {
    if (autoFitTimeout) {
        clearTimeout(autoFitTimeout);
        autoFitTimeout = null;
    }
}

async function refreshData() {
    await loadKnowledgeGraph();
}

function fitToScreen() {
    if (!svg || !container || !zoom || graphData.nodes.length === 0) return;

    try {
        // Calculate bounds from actual node positions
        const padding = 50;
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

        graphData.nodes.forEach(node => {
            if (node.x !== undefined && node.y !== undefined) {
                minX = Math.min(minX, node.x);
                maxX = Math.max(maxX, node.x);
                minY = Math.min(minY, node.y);
                maxY = Math.max(maxY, node.y);
            }
        });

        const boundsWidth = maxX - minX + padding * 2;
        const boundsHeight = maxY - minY + padding * 2;
        const boundsX = minX - padding;
        const boundsY = minY - padding;

        const fullWidth = width;
        const fullHeight = height;
        const scale = Math.min(fullWidth / boundsWidth, fullHeight / boundsHeight) * 0.9;

        const translate = [
            fullWidth / 2 - scale * (boundsX + boundsWidth / 2),
            fullHeight / 2 - scale * (boundsY + boundsHeight / 2)
        ];

        svg.transition()
            .duration(750)
            .call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
    } catch (error) {
        console.error('Error fitting to screen:', error);
    }
}

let contextMenuNode = null;

function showContextMenu(event, node) {
    const menu = document.getElementById('contextMenu');
    contextMenuNode = node;

    menu.style.left = event.pageX + 'px';
    menu.style.top = event.pageY + 'px';
    menu.style.display = 'block';
}

function hideContextMenu() {
    const menu = document.getElementById('contextMenu');
    menu.style.display = 'none';
    contextMenuNode = null;
}

function zoomToNode() {
    if (!contextMenuNode || !svg || !zoom) {
        hideContextMenu();
        return;
    }

    const node = contextMenuNode;
    hideContextMenu();

    // Cancel auto-fit
    cancelAutoFit();

    // Highlight the node
    highlightNode(node.id);

    // Center on the node at zoom level 1.0
    const translateX = width / 2 - node.x;
    const translateY = height / 2 - node.y;

    svg.transition()
        .duration(750)
        .call(zoom.transform, d3.zoomIdentity.translate(translateX, translateY).scale(1));
}

function zoomToNodeByName(nodeName) {
    if (!svg || !zoom) return;

    // Cancel auto-fit
    cancelAutoFit();

    // Find the node data
    const node = graphData.nodes.find(n => n.id === nodeName);
    if (!node) {
        console.error('Node not found:', nodeName);
        return;
    }

    // Highlight the node
    highlightNode(nodeName);

    // Show details for this entity
    showEntityDetails(nodeName);

    // Center on the node at zoom level 1.0
    const translateX = width / 2 - node.x;
    const translateY = height / 2 - node.y;

    svg.transition()
        .duration(750)
        .call(zoom.transform, d3.zoomIdentity.translate(translateX, translateY).scale(1));
}

function showNodeDetails() {
    if (!contextMenuNode) {
        hideContextMenu();
        return;
    }

    showEntityDetails(contextMenuNode.id);
    hideContextMenu();
}

function centerGraph() {
    if (!svg || !container || !zoom || graphData.nodes.length === 0) return;

    try {
        // Center the graph at current zoom level
        const currentTransform = d3.zoomTransform(svg.node());
        const bounds = container.node().getBBox();
        const centerX = width / 2 - currentTransform.k * (bounds.x + bounds.width / 2);
        const centerY = height / 2 - currentTransform.k * (bounds.y + bounds.height / 2);

        svg.transition()
            .duration(750)
            .call(zoom.transform, d3.zoomIdentity.translate(centerX, centerY).scale(currentTransform.k));
    } catch (error) {
        console.error('Error centering graph:', error);
    }
}

function toggleSimulation() {
    const btn = document.getElementById('pauseBtn');
    if (simulation.alpha() > 0) {
        simulation.stop();
        btn.textContent = 'Resume';
    } else {
        simulation.restart();
        btn.textContent = 'Pause';
    }
}

// Debug function to force layout restart
function forceLayout() {
    console.log('Manually forcing layout restart');

    // Randomize positions to break any clustering
    graphData.nodes.forEach(d => {
        d.x = width/2 + (Math.random() - 0.5) * 300;
        d.y = height/2 + (Math.random() - 0.5) * 300;
        d.vx = (Math.random() - 0.5) * 100;
        d.vy = (Math.random() - 0.5) * 100;
        // Clear any fixed positions
        delete d.fx;
        delete d.fy;
    });

    // Force strong restart
    simulation.alpha(1.0).alphaTarget(0.3).restart();

    setTimeout(() => {
        simulation.alphaTarget(0);
    }, 5000);
}

// Make it available globally for debugging
window.forceLayout = forceLayout;

// Drag handlers
function dragstarted(event, d) {
    // Cancel auto-fit and stop simulation settling on any drag
    cancelAutoFit();
    simulation.stop();

    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// Event listeners
document.addEventListener('click', function(event) {
    // Hide context menu when clicking anywhere except on it
    const contextMenu = document.getElementById('contextMenu');
    if (contextMenu && !contextMenu.contains(event.target)) {
        hideContextMenu();
    }
});

document.getElementById('searchInput').addEventListener('input', function(e) {
    const query = e.target.value;
    if (query.length >= 2) {
        showSearchResults(query);
    } else {
        document.getElementById('searchResults').innerHTML = '';
    }
});

document.getElementById('searchInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        const query = e.target.value;
        if (query.length >= 2) {
            showSearchResults(query);
        }
    }
});

// Expose functions to global scope for inline onclick handlers
window.loadKnowledgeGraph = loadKnowledgeGraph;
window.fitToScreen = fitToScreen;
window.centerGraph = centerGraph;
window.toggleSimulation = toggleSimulation;
window.toggleSearch = toggleSearch;
window.refreshData = refreshData;
window.zoomToNode = zoomToNode;
window.zoomToNodeByName = zoomToNodeByName;
window.showNodeDetails = showNodeDetails;
window.showEntityDetails = showEntityDetails;
window.clearSearch = clearSearch;
window.closeDetail = closeDetail;

// Auto-load graph when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadKnowledgeGraph().catch(err => console.error('Error loading graph:', err));
    });
} else {
    loadKnowledgeGraph().catch(err => console.error('Error loading graph:', err));
}
