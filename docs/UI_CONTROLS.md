![Zabob Banner](../.dev-library/docs-assets/images/zabob-banner-memgraph.jpg)
<!-- markdownlint-disable-file MD036 -->
# UI Controls Documentation

## Graph Navigation

### Mouse Controls

- **Left-click node**: Show entity details with "Zoom to Node" button
- **Right-click node** (or **Ctrl+Click**): Open context menu with:
  - **Zoom to Node**: Focus on node at 1:1 scale
  - **Show Details**: Open detail panel
- **Click and drag background**: Pan the view
- **Mouse wheel**: Zoom in/out

**Note**: Some browsers (like VS Code Simple Browser) may not support right-click context menus. Use **Ctrl+Click** (Windows/Linux) or **Cmd+Click** (Mac) as an alternative, or simply click the node to view details and use the "🔍 Zoom to This Node" button in the details panel.

### Button Controls

#### Fit All

Shows all nodes at optimal zoom level. Perfect for getting an overview of the entire graph.

#### Center

Centers the graph at current zoom level. Use this to reorient without changing zoom.

#### Pause/Resume

Pauses/resumes the force simulation animation.

#### Search

Opens search panel to find entities by name or observation.

#### Refresh

Reloads graph data from server.

## The "Zoom to Node" Feature

The most useful zoom feature is accessed by **right-clicking any node** and selecting "Zoom to Node":

- Sets zoom to 1:1 scale (great for reading labels)
- Centers that specific node in the viewport
- Perfect for examining a particular entity in detail

This replaces the old "Reset Zoom" button which wasn't intuitive (1:1 scale is too zoomed in for large graphs).

## Tips

- Use **Fit All** to see everything at once
- **Right-click + Zoom to Node** to focus on specific entities
- **Center** to reorient without losing your current zoom level
- Use mouse wheel or trackpad pinch to zoom in/out smoothly
