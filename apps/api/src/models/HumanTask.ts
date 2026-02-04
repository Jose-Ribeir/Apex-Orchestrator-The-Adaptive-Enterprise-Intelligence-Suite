import {
  Model,
  DataTypes,
  Optional,
  BelongsToGetAssociationMixin,
} from "sequelize";
import type { ModelQuery } from "./ModelQuery";
import { sequelize } from "../config/database";

export type HumanTaskStatus = "PENDING" | "RESOLVED";

export interface HumanTaskAttributes {
  id: string;
  modelQueryId: string;
  reason: string;
  retrievedData?: string | null;
  modelMessage: string;
  status: HumanTaskStatus;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type HumanTaskCreationAttributes = Optional<
  HumanTaskAttributes,
  | "id"
  | "status"
  | "retrievedData"
  | "createdAt"
  | "updatedAt"
  | "isDeleted"
  | "deletedAt"
>;

export class HumanTask
  extends Model<HumanTaskAttributes, HumanTaskCreationAttributes>
  implements HumanTaskAttributes
{
  declare id: string;
  declare modelQueryId: string;
  declare reason: string;
  declare retrievedData: string | null;
  declare modelMessage: string;
  declare status: HumanTaskStatus;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;

  declare getModelQuery: BelongsToGetAssociationMixin<ModelQuery>;
}

HumanTask.init(
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
    reason: {
      type: DataTypes.TEXT,
      allowNull: false,
    },
    retrievedData: {
      type: DataTypes.TEXT,
      allowNull: true,
      field: "retrieved_data",
    },
    modelMessage: {
      type: DataTypes.TEXT,
      allowNull: false,
      field: "model_message",
    },
    status: {
      type: DataTypes.ENUM("PENDING", "RESOLVED"),
      allowNull: false,
      defaultValue: "PENDING",
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
    tableName: "human_tasks",
  },
);
