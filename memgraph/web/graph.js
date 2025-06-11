/**
 * Knowledge Graph D3.js Visualization
 * HTTP-based client that fetches data from the MCP server
 */

// Global variables
const width = window.innerWidth;
const height = window.innerHeight;
let graphData = { nodes: [], links: [] };
let searchIndex = [];
let simulation;
let svg, container;

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

    const zoom = d3.zoom()
        .scaleExtent([0.1, 10])
        .on("zoom", function(event) {
            container.attr("transform", event.transform);
        });

    svg.call(zoom);
    container = svg.append("g");

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

// Load knowledge graph data from the server
async function loadKnowledgeGraph() {
    const loadingEl = document.getElementById('loading');
    loadingEl.style.display = 'flex';
    
    const startTime = performance.now();
    
    try {
        const response = await fetch('/api/knowledge-graph');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        const loadTime = Math.round(performance.now() - startTime);
        
        // Initialize visualization if not done yet
        if (!svg) {
            initializeVisualization();
        }
        
        // Update the visualization
        updateKnowledgeGraph(data.nodes, data.links);
        
        // Update stats
        document.getElementById('loadTime').textContent = `Load: ${loadTime}ms`;
        
        console.log('Knowledge graph loaded:', data.stats);
        
    } catch (error) {
        console.error('Failed to load knowledge graph:', error);
        showError(`Failed to load knowledge graph: ${error.message}`);
    } finally {
        loadingEl.style.display = 'none';
    }
}

// Update the graph visualization
function updateKnowledgeGraph(nodes, links) {
    // Store the data and give nodes initial positions
    graphData.nodes = nodes.map(d => ({
        ...d,
        x: width/2 + (Math.random() - 0.5) * 200,  // Spread around center
        y: height/2 + (Math.random() - 0.5) * 200,
        vx: (Math.random() - 0.5) * 50,  // Initial velocity to break clustering
        vy: (Math.random() - 0.5) * 50
    }));
    graphData.links = links.map(d => ({...d}));
    
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
        
    nodeUpdate.on('click', function(event, d) {
        event.stopPropagation();
        showEntityDetails(d.id);
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

    // Update simulation with proper restart
    simulation.nodes(graphData.nodes);
    simulation.force("link").links(graphData.links);
    
    console.log('Force simulation restarting with alpha 1.0');
    
    // Force restart with very high alpha for strong initial layout
    simulation.alpha(1.0).alphaTarget(0.3).restart();
    
    // Remove alpha target after longer settling period
    setTimeout(() => {
        console.log('Removing alphaTarget, allowing natural cooling');
        simulation.alphaTarget(0);
    }, 5000);
    
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

    // Auto-fit after simulation has settled longer
    setTimeout(fitToScreen, 6000);
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
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error(`Search failed: ${response.statusText}`);
        }
        return await response.json();
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
    
    container.innerHTML = results.map(result => {
        const snippet = result.content.length > 120 ? 
            result.content.substring(0, 120) + '...' : 
            result.content;
            
        return `
            <div class="search-result" onclick="showEntityDetails('${result.entity}', ${result.observationIndex || 'null'})">
                <div class="result-title">${highlightText(result.entity, query)}</div>
                <div class="result-type">${result.entityType} • ${result.type}</div>
                <div class="result-snippet">${highlightText(snippet, query)}</div>
            </div>
        `;
    }).join('');
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
    svg.selectAll('.node')
        .transition()
        .duration(300)
        .attr('stroke', d => d.id === entityName ? '#ff6b35' : '#fff')
        .attr('stroke-width', d => d.id === entityName ? 3 : 1.5);
        
    // Reset after 2 seconds
    setTimeout(() => {
        svg.selectAll('.node')
            .transition()
            .duration(300)
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5);
    }, 2000);
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

function closeDetail() {
    document.getElementById('detailPanel').style.display = 'none';
}

async function refreshData() {
    await loadKnowledgeGraph();
}

function fitToScreen() {
    if (graphData.nodes.length === 0) return;
    
    const bounds = container.node().getBBox();
    const fullWidth = width;
    const fullHeight = height;
    const widthScale = fullWidth / bounds.width;
    const heightScale = fullHeight / bounds.height;
    const scale = Math.min(widthScale, heightScale) * 0.8;
    const translate = [fullWidth / 2 - scale * (bounds.x + bounds.width / 2),
                    fullHeight / 2 - scale * (bounds.y + bounds.height / 2)];

    svg.transition()
        .duration(750)
        .call(d3.zoom().transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
}

function resetZoom() {
    svg.transition()
        .duration(750)
        .call(d3.zoom().transform, d3.zoomIdentity);
}

function centerGraph() {
    svg.transition()
        .duration(750)
        .call(d3.zoom().transform, d3.zoomIdentity.translate(width/2, height/2));
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
