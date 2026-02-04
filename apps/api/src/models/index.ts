import { Agent } from "./Agent";
import { AgentInstruction } from "./AgentInstruction";
import { Tool } from "./Tool";
import { AgentTool } from "./AgentTool";
import { ModelQuery } from "./ModelQuery";
import { HumanTask } from "./HumanTask";
import { PerformanceMetric } from "./PerformanceMetric";
import { DailyStat } from "./DailyStat";
import { Notification } from "./Notification";
import { ApiToken } from "./ApiToken";

// Agent <-> AgentInstruction (1:N)
Agent.hasMany(AgentInstruction, { foreignKey: "agentId", as: "instructions" });
AgentInstruction.belongsTo(Agent, { foreignKey: "agentId", as: "agent" });

// Agent <-> Tool (N:M via AgentTool)
Agent.belongsToMany(Tool, {
  through: AgentTool,
  foreignKey: "agentId",
  otherKey: "toolId",
  as: "tools",
});
Tool.belongsToMany(Agent, {
  through: AgentTool,
  foreignKey: "toolId",
  otherKey: "agentId",
  as: "agents",
});
Agent.hasMany(AgentTool, { foreignKey: "agentId" });
AgentTool.belongsTo(Agent, { foreignKey: "agentId" });
Tool.hasMany(AgentTool, { foreignKey: "toolId" });
AgentTool.belongsTo(Tool, { foreignKey: "toolId" });

// Agent <-> ModelQuery (1:N)
Agent.hasMany(ModelQuery, { foreignKey: "agentId", as: "queries" });
ModelQuery.belongsTo(Agent, { foreignKey: "agentId", as: "agent" });

// ModelQuery <-> HumanTask (1:1)
ModelQuery.hasOne(HumanTask, { foreignKey: "modelQueryId", as: "humanTask" });
HumanTask.belongsTo(ModelQuery, {
  foreignKey: "modelQueryId",
  as: "modelQuery",
});

// ModelQuery <-> PerformanceMetric (1:1)
ModelQuery.hasOne(PerformanceMetric, {
  foreignKey: "modelQueryId",
  as: "metrics",
});
PerformanceMetric.belongsTo(ModelQuery, {
  foreignKey: "modelQueryId",
  as: "modelQuery",
});

// Agent <-> DailyStat (1:N)
Agent.hasMany(DailyStat, { foreignKey: "agentId", as: "stats" });
DailyStat.belongsTo(Agent, { foreignKey: "agentId", as: "agent" });

export {
  Agent,
  AgentInstruction,
  Tool,
  AgentTool,
  ModelQuery,
  HumanTask,
  PerformanceMetric,
  DailyStat,
  Notification,
  ApiToken,
};
