import {
  Model,
  DataTypes,
  Optional,
  BelongsToGetAssociationMixin,
  HasOneGetAssociationMixin,
} from "sequelize";
import type { Agent } from "./Agent";
import type { HumanTask } from "./HumanTask";
import type { PerformanceMetric } from "./PerformanceMetric";
import { sequelize } from "../config/database";

export type QueryMethod = "PERFORMANCE" | "EFFICIENCY";

export interface ModelQueryAttributes {
  id: string;
  agentId: string;
  userQuery: string;
  modelResponse?: string | null;
  methodUsed: QueryMethod;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type ModelQueryCreationAttributes = Optional<
  ModelQueryAttributes,
  "id" | "modelResponse" | "createdAt" | "updatedAt" | "isDeleted" | "deletedAt"
>;

export class ModelQuery
  extends Model<ModelQueryAttributes, ModelQueryCreationAttributes>
  implements ModelQueryAttributes
{
  declare id: string;
  declare agentId: string;
  declare userQuery: string;
  declare modelResponse: string | null;
  declare methodUsed: QueryMethod;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;

  declare getAgent: BelongsToGetAssociationMixin<Agent>;
  declare getHumanTask: HasOneGetAssociationMixin<HumanTask>;
  declare getMetrics: HasOneGetAssociationMixin<PerformanceMetric>;
}

ModelQuery.init(
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
    userQuery: {
      type: DataTypes.TEXT,
      allowNull: false,
      field: "user_query",
    },
    modelResponse: {
      type: DataTypes.TEXT,
      allowNull: true,
      field: "model_response",
    },
    methodUsed: {
      type: DataTypes.ENUM("PERFORMANCE", "EFFICIENCY"),
      allowNull: false,
      field: "method_used",
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
    tableName: "model_queries",
    indexes: [{ fields: ["agent_id"] }],
    defaultScope: { where: { isDeleted: false } },
  },
);
