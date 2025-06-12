import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdIo.js";

const run_client = async (url) => {
    if (!url) {
        console.log('Connecting to Model Context Protocol server at:', url || 'stdio');
    }
    const transport = (
        url
        ? new StreamableHTTPClientTransport(url)
        : new StdioClientTransport({
            command: 'python3',
            args: ['memgraph/mcp_service.py'],
        })
    );
    const client = new Client(
    {
        name: "example-client",
        version: "1.0.0"
    }
    );

    try {
        await client.connect(transport);

        // Call a tool
        let result = await client.callTool({
        name: "read_graph",
        arguments: {}
        });
        console.log('Tool call result:', result);
        result = await client.callTool({
            name: "search_nodes",
            arguments: {
                query: "zabob"
            }
        });
        console.log('Tool call result:', result);
    } catch (error) {
        console.error('Error during client operation:', error);
    }
};

const isBrowser = () => {
  return typeof window !== 'undefined' && typeof document !== 'undefined';
};

if (!isBrowser()) {
    // If not running in a browser, execute the client
    run_client(process.argv[2]);
}
