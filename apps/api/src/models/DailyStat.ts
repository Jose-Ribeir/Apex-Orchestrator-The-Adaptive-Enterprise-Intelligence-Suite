import {
  Model,
  DataTypes,
  Optional,
  BelongsToGetAssociationMixin,
} from "sequelize";
import type { Agent } from "./Agent";
import { sequelize } from "../config/database";

export interface DailyStatAttributes {
  id: string;
  agentId: string;
  date: Date;
  totalQueries: number;
  totalTokens: number;
  avgEfficiency?: number | null;
  avgQuality?: number | null;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type DailyStatCreationAttributes = Optional<
  DailyStatAttributes,
  | "id"
  | "avgEfficiency"
  | "avgQuality"
  | "createdAt"
  | "updatedAt"
  | "isDeleted"
  | "deletedAt"
>;

export class DailyStat
  extends Model<DailyStatAttributes, DailyStatCreationAttributes>
  implements DailyStatAttributes
{
  declare id: string;
  declare agentId: string;
  declare date: Date;
  declare totalQueries: number;
  declare totalTokens: number;
  declare avgEfficiency: number | null;
  declare avgQuality: number | null;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;

  declare getAgent: BelongsToGetAssociationMixin<Agent>;
}

DailyStat.init(
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
    date: {
      type: DataTypes.DATEONLY,
      allowNull: false,
    },
    totalQueries: {
      type: DataTypes.INTEGER,
      allowNull: false,
      field: "total_queries",
    },
    totalTokens: {
      type: DataTypes.INTEGER,
      allowNull: false,
      field: "total_tokens",
    },
    avgEfficiency: {
      type: DataTypes.FLOAT,
      allowNull: true,
      field: "avg_efficiency",
    },
    avgQuality: {
      type: DataTypes.FLOAT,
      allowNull: true,
      field: "avg_quality",
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
    tableName: "daily_stats",
    indexes: [{ unique: true, fields: ["agent_id", "date"] }],
  },
);
