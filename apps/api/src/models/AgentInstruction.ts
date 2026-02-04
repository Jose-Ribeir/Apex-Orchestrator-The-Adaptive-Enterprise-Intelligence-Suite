import {
  Model,
  DataTypes,
  Optional,
  BelongsToGetAssociationMixin,
} from "sequelize";
import type { Agent } from "./Agent";
import { sequelize } from "../config/database";

export interface AgentInstructionAttributes {
  id: string;
  agentId: string;
  content: string;
  order: number;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type AgentInstructionCreationAttributes = Optional<
  AgentInstructionAttributes,
  "id" | "createdAt" | "updatedAt" | "isDeleted" | "deletedAt"
>;

export class AgentInstruction
  extends Model<AgentInstructionAttributes, AgentInstructionCreationAttributes>
  implements AgentInstructionAttributes
{
  declare id: string;
  declare agentId: string;
  declare content: string;
  declare order: number;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;

  declare getAgent: BelongsToGetAssociationMixin<Agent>;
}

AgentInstruction.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    agentId: {
      type: DataTypes.UUID,
      allowNull: false,
      field: "agent_id",
    },
    content: {
      type: DataTypes.TEXT,
      allowNull: false,
    },
    order: {
      type: DataTypes.INTEGER,
      allowNull: false,
    },
    isDeleted: {
      type: DataTypes.BOOLEAN,
      defaultValue: false,
      field: "is_deleted",
    },
    deletedAt: {
      type: DataTypes.DATE,
      allowNull: true,
      field: "deleted_at",
    },
  },
  {
    sequelize,
    tableName: "agent_instructions",
    indexes: [{ fields: ["agent_id"] }],
  },
);
