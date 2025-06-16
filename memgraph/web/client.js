import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdIo.js";

const run_client = async (transportType, url, servicePath) => {
    console.log(`Connecting to Model Context Protocol server via ${transportType}:`, url || servicePath || 'stdio');

    let transport;
    if (transportType === 'http' && url) {
        transport = new StreamableHTTPClientTransport(url);
    } else if (transportType === 'stdio' && servicePath && url) {
        transport = new StdioClientTransport({
            command: 'python3',
            args: [servicePath],
        });
    } else {
        console.error('Invalid transport type or missing URL/service path.');
        return;
    }
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
    // Parse command line arguments
    const args = process.argv.slice(2);
    let transportType = null;
    let url = null;
    let servicePath = null;

    // Parse --transport, --url, --service-path arguments
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--transport' && i + 1 < args.length) {
            transportType = args[i + 1];
            i++;
        } else if (args[i] === '--url' && i + 1 < args.length) {
            url = args[i + 1];
            i++;
        } else if (args[i] === '--service-path' && i + 1 < args.length) {
            servicePath = args[i + 1];
            i++;
        } else if (!transportType && !url && !servicePath) {
            // Backward compatibility: first arg is URL
            url = args[i];
        }
    }

    // If not running in a browser, execute the client
    run_client(transportType, url, servicePath);
}
