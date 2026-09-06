import type {TreeNode} from '../types/domain';

const labels:Record<string,string>={
  functional_location:'FL',
  equipment:'EQ',
  sub_equipment:'SE',
  assembly:'ASM',
  component:'CMP',
  stand:'STD',
  stand_system:'SYS',
};

function Node({node,depth}:{node:TreeNode;depth:number}){
  const label=labels[node.type]||node.type.slice(0,3).toUpperCase();
  return <div>
    <div className="tree-row" style={{paddingLeft:12+depth*20}}>
      <span className="badge">{label}</span>
      <span>{node.code||'—'}</span>
      <strong>{node.name}</strong>
      {node.status&&<span className="status">{node.status}</span>}
    </div>
    {node.children.map(child=><Node key={child.id} node={child} depth={depth+1}/>)}
  </div>;
}

export function Tree({nodes}:{nodes:TreeNode[]}){
  return <div className="tree">{nodes.map(node=><Node key={node.id} node={node} depth={0}/>)}</div>;
}
