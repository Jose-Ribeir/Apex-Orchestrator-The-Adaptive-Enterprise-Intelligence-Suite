import { Model, DataTypes, Optional } from "sequelize";
import { sequelize } from "../config/database";

export interface AgentToolAttributes {
  agentId: string;
  toolId: string;
  createdAt?: Date;
}

export type AgentToolCreationAttributes = Optional<
  AgentToolAttributes,
  "createdAt"
>;

export class AgentTool
  extends Model<AgentToolAttributes, AgentToolCreationAttributes>
  implements AgentToolAttributes
{
  declare agentId: string;
  declare toolId: string;
  declare readonly createdAt: Date;
}

AgentTool.init(
  {
    agentId: {
      type: DataTypes.UUID,
      allowNull: false,
      primaryKey: true,
      field: "agent_id",
    },
    toolId: {
      type: DataTypes.UUID,
      allowNull: false,
      primaryKey: true,
      field: "tool_id",
    },
  },
  {
    sequelize,
    tableName: "agent_tools",
    timestamps: true,
    updatedAt: false,
  },
);
