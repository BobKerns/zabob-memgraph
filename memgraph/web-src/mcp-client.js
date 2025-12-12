/**
 * Browser MCP Client for Knowledge Graph
 * 
 * Provides a simple interface for the browser to call MCP tools.
 */

console.log('[mcp-client.js] Module loading...');

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

console.log('[mcp-client.js] SDK imported:', { Client, StreamableHTTPClientTransport });

let mcpClient = null;
let mcpTransport = null;

/**
 * Initialize the MCP client connection
 * @param {string} baseUrl - Base URL for the MCP server (default: window.location.origin)
 * @returns {Promise<void>}
 */
export async function initMCPClient(baseUrl = window.location.origin) {
    if (mcpClient) {
        console.log('MCP client already initialized');
        return;
    }

    try {
        console.log('Initializing MCP client with base URL:', baseUrl);
        
        // Create HTTP+SSE transport to /mcp endpoint
        mcpTransport = new StreamableHTTPClientTransport(`${baseUrl}/mcp`);
        
        // Create MCP client
        mcpClient = new Client({
            name: "knowledge-graph-ui",
            version: "1.0.0"
        });

        // Connect to the server
        await mcpClient.connect(mcpTransport);
        
        console.log('MCP client connected successfully');
    } catch (error) {
        console.error('Failed to initialize MCP client:', error);
        throw error;
    }
}

/**
 * Read the complete knowledge graph
 * @param {string} name - Graph identifier (default: 'default')
 * @returns {Promise<Object>} Graph data with entities, relations, and observations
 */
export async function readGraph(name = 'default') {
    if (!mcpClient) {
        throw new Error('MCP client not initialized. Call initMCPClient() first.');
    }

    try {
        const result = await mcpClient.callTool({
            name: "read_graph",
            arguments: { name }
        });

        // Extract data from MCP response
        // MCP tool results are in result.content array
        if (result.content && result.content.length > 0) {
            const content = result.content[0];
            if (content.type === 'text') {
                return JSON.parse(content.text);
            }
        }
        
        throw new Error('Unexpected MCP response format');
    } catch (error) {
        console.error('Failed to read graph:', error);
        throw error;
    }
}

/**
 * Search the knowledge graph
 * @param {string} query - Search query string
 * @returns {Promise<Object>} Search results with matching entities
 */
export async function searchNodes(query) {
    if (!mcpClient) {
        throw new Error('MCP client not initialized. Call initMCPClient() first.');
    }

    try {
        const result = await mcpClient.callTool({
            name: "search_nodes",
            arguments: { query }
        });

        // Extract data from MCP response
        if (result.content && result.content.length > 0) {
            const content = result.content[0];
            if (content.type === 'text') {
                return JSON.parse(content.text);
            }
        }
        
        throw new Error('Unexpected MCP response format');
    } catch (error) {
        console.error('Failed to search nodes:', error);
        throw error;
    }
}

/**
 * Get knowledge graph statistics
 * @returns {Promise<Object>} Statistics about the graph
 */
export async function getStats() {
    if (!mcpClient) {
        throw new Error('MCP client not initialized. Call initMCPClient() first.');
    }

    try {
        const result = await mcpClient.callTool({
            name: "get_stats",
            arguments: {}
        });

        // Extract data from MCP response
        if (result.content && result.content.length > 0) {
            const content = result.content[0];
            if (content.type === 'text') {
                return JSON.parse(content.text);
            }
        }
        
        throw new Error('Unexpected MCP response format');
    } catch (error) {
        console.error('Failed to get stats:', error);
        throw error;
    }
}

/**
 * Close the MCP client connection
 */
export async function closeMCPClient() {
    if (mcpClient) {
        try {
            await mcpClient.close();
            mcpClient = null;
            mcpTransport = null;
            console.log('MCP client closed');
        } catch (error) {
            console.error('Error closing MCP client:', error);
        }
    }
}
