import {
  Model,
  DataTypes,
  Optional,
  BelongsToGetAssociationMixin,
} from "sequelize";
import type { ModelQuery } from "./ModelQuery";
import { sequelize } from "../config/database";

export interface PerformanceMetricAttributes {
  id: string;
  modelQueryId: string;
  tokenUsage: number;
  responseTimeMs?: number | null;
  efficiencyScore?: number | null;
  qualityScore?: number | null;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type PerformanceMetricCreationAttributes = Optional<
  PerformanceMetricAttributes,
  | "id"
  | "responseTimeMs"
  | "efficiencyScore"
  | "qualityScore"
  | "createdAt"
  | "updatedAt"
  | "isDeleted"
  | "deletedAt"
>;

export class PerformanceMetric
  extends Model<
    PerformanceMetricAttributes,
    PerformanceMetricCreationAttributes
  >
  implements PerformanceMetricAttributes
{
  declare id: string;
  declare modelQueryId: string;
  declare tokenUsage: number;
  declare responseTimeMs: number | null;
  declare efficiencyScore: number | null;
  declare qualityScore: number | null;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;

  declare getModelQuery: BelongsToGetAssociationMixin<ModelQuery>;
}

PerformanceMetric.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    modelQueryId: {
      type: DataTypes.UUID,
      allowNull: false,
      unique: true,
      field: "model_query_id",
    },
    tokenUsage: {
      type: DataTypes.INTEGER,
      allowNull: false,
      field: "token_usage",
    },
    responseTimeMs: {
      type: DataTypes.INTEGER,
      allowNull: true,
      field: "response_time_ms",
    },
    efficiencyScore: {
      type: DataTypes.FLOAT,
      allowNull: true,
      field: "efficiency_score",
    },
    qualityScore: {
      type: DataTypes.FLOAT,
      allowNull: true,
      field: "quality_score",
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
    tableName: "performance_metrics",
    defaultScope: { where: { isDeleted: false } },
  },
);
