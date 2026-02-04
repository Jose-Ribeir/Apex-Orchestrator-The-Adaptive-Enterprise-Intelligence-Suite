import {
  Model,
  DataTypes,
  Optional,
  HasManyGetAssociationsMixin,
  HasManyAddAssociationMixin,
  HasManySetAssociationsMixin,
  BelongsToManyGetAssociationsMixin,
  BelongsToManyAddAssociationMixin,
  BelongsToManySetAssociationsMixin,
} from "sequelize";
import type { AgentInstruction } from "./AgentInstruction";
import type { AgentTool } from "./AgentTool";
import type { ModelQuery } from "./ModelQuery";
import type { DailyStat } from "./DailyStat";
import type { Tool } from "./Tool";
import { sequelize } from "../config/database";

export type AgentMode = "PERFORMANCE" | "EFFICIENCY";

export interface AgentAttributes {
  id: string;
  userId: string;
  name: string;
  mode: AgentMode;
  prompt: string | null;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type AgentCreationAttributes = Optional<
  AgentAttributes,
  "id" | "createdAt" | "updatedAt" | "isDeleted" | "deletedAt" | "prompt"
>;

export class Agent
  extends Model<AgentAttributes, AgentCreationAttributes>
  implements AgentAttributes
{
  declare id: string;
  declare userId: string;
  declare name: string;
  declare mode: AgentMode;
  declare prompt: string | null;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;

  declare getInstructions: HasManyGetAssociationsMixin<AgentInstruction>;
  declare addInstruction: HasManyAddAssociationMixin<AgentInstruction, string>;
  declare setInstructions: HasManySetAssociationsMixin<
    AgentInstruction,
    string
  >;

  declare getAgentTools: HasManyGetAssociationsMixin<AgentTool>;
  declare getTools: BelongsToManyGetAssociationsMixin<Tool>;
  declare addTool: BelongsToManyAddAssociationMixin<Tool, string>;
  declare setTools: BelongsToManySetAssociationsMixin<Tool, string>;

  declare getQueries: HasManyGetAssociationsMixin<ModelQuery>;
  declare getDailyStats: HasManyGetAssociationsMixin<DailyStat>;
}

Agent.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    userId: {
      type: DataTypes.STRING,
      allowNull: false,
      field: "user_id",
    },
    name: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    mode: {
      type: DataTypes.ENUM("PERFORMANCE", "EFFICIENCY"),
      allowNull: false,
    },
    prompt: {
      type: DataTypes.TEXT,
      allowNull: true,
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
    tableName: "agents",
    indexes: [{ fields: ["user_id"] }],
  },
);
