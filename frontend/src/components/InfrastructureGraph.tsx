import { useMemo } from 'react';
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Asset, ConnectionData, GraphEdge, GraphNode } from '../services/api';

export type AssetFlowNode = Node<Asset, 'asset'>;
export type ConnectionFlowEdge = Edge<ConnectionData>;

function shortLabel(value: string | null | undefined): string {
  if (!value) return 'n/a';
  return value.length > 24 ? `${value.slice(0, 21)}...` : value;
}

function AssetNodeCard({ data, selected }: NodeProps<AssetFlowNode>) {
  const criticality = String(data.criticality || 'unknown').toLowerCase();
  const exposure = String(data.exposure || 'unknown').toLowerCase();
  const riskLevel = String(data.risk_level || '').toLowerCase();
  return (
    <div className={`graph-node-card risk-${riskLevel || 'unknown'} criticality-${criticality}${selected ? ' selected' : ''}`}>
      <div className="graph-node-header">
        <span className="graph-node-kind">{String(data.type || 'asset')}</span>
        <span className={`graph-node-badge exposure-${exposure}`}>{String(data.exposure || 'unknown')}</span>
      </div>
      <strong className="graph-node-name">{String(data.name || data.id)}</strong>
      <div className="graph-node-meta">
        <span>{String(data.id)}</span>
        <span>{String(data.ip || 'no ip')}</span>
      </div>
      <div className="graph-node-meta">
        <span>Ports: {Array.isArray(data.ports) && data.ports.length ? data.ports.join(', ') : 'none'}</span>
        <span className={`criticality-text ${criticality}`}>{String(data.criticality || 'unknown')}</span>
      </div>
      <div className="graph-node-meta">
        <span>Risk: {data.risk_score != null ? `${data.risk_score}/100` : 'unavailable'}</span>
        <span className={`risk-text ${riskLevel || 'unknown'}`}>{riskLevel || 'unknown'}</span>
      </div>
    </div>
  );
}

const nodeTypes = {
  asset: AssetNodeCard,
};

function toFlowNode(node: GraphNode): AssetFlowNode {
  return {
    id: node.id,
    type: 'asset',
    position: node.position || { x: 0, y: 0 },
    data: node.data,
    draggable: true,
  };
}

function edgeLabel(edge: GraphEdge): string {
  if (edge.label) return edge.label;
  const protocol = edge.data?.protocol ? edge.data.protocol.toUpperCase() : 'TCP';
  const port = edge.data?.port != null ? `:${edge.data.port}` : '';
  return `${protocol}${port}`;
}

function toFlowEdge(edge: GraphEdge): ConnectionFlowEdge {
  const allowed = edge.data?.allowed;
  const stroke = allowed === false ? '#ed8b74' : '#4cc8b0';
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    label: edgeLabel(edge),
    data: edge.data,
    animated: allowed === true,
    markerEnd: { type: MarkerType.ArrowClosed, color: stroke },
    style: { stroke, strokeWidth: 2 },
    labelStyle: { fill: '#d6ebe5', fontSize: 10, fontWeight: 600 },
    labelBgStyle: { fill: '#0a242b', fillOpacity: 0.9 },
    labelBgPadding: [4, 2],
    labelBgBorderRadius: 3,
  };
}

interface InfrastructureGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedAssetId: string | null;
  onSelectAsset: (assetId: string | null) => void;
}

export default function InfrastructureGraph({ nodes, edges, selectedAssetId, onSelectAsset }: InfrastructureGraphProps) {
  const flowNodes = useMemo(() => toFlowNodes(nodes, selectedAssetId), [nodes, selectedAssetId]);
  const flowEdges = useMemo(() => edges.map(toFlowEdge), [edges]);

  const onNodeClick: NodeMouseHandler = (_, node) => {
    onSelectAsset(node.id);
  };

  return (
    <div className="graph-canvas" aria-label="Interactive network topology graph">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={() => onSelectAsset(null)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} size={1} color="rgba(204,239,228,0.08)" />
        <MiniMap
          pannable
          zoomable
          nodeColor={(node) => {
            const data = (node.data || {}) as Partial<Asset>;
            const risk = String(data.risk_level || '').toLowerCase();
            if (risk === 'high') return '#ed8b74';
            if (risk === 'medium') return '#f0c478';
            if (risk === 'low') return '#4cc8b0';
            return '#7e99b2';
          }}
          maskColor="rgba(6, 19, 27, 0.7)"
        />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function toFlowNodes(nodes: GraphNode[], selectedAssetId: string | null): AssetFlowNode[] {
  return nodes.map((node) => ({
    ...toFlowNode(node),
    selected: node.id === selectedAssetId,
  }));
}

export { shortLabel };
