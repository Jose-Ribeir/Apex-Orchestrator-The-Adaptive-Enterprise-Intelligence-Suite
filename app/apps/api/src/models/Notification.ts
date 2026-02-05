import { Model, DataTypes, Optional } from "sequelize";
import { sequelize } from "../config/database";

export type NotificationType =
  | "HUMAN_TASK_CREATED"
  | "AGENT_ERROR"
  | "PERFORMANCE_ALERT"
  | "SYSTEM";

export interface NotificationAttributes {
  id: string;
  userId: string;
  type: NotificationType;
  title: string;
  message: string;
  isRead: boolean;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type NotificationCreationAttributes = Optional<
  NotificationAttributes,
  "id" | "isRead" | "createdAt" | "updatedAt" | "isDeleted" | "deletedAt"
>;

export class Notification
  extends Model<NotificationAttributes, NotificationCreationAttributes>
  implements NotificationAttributes
{
  declare id: string;
  declare userId: string;
  declare type: NotificationType;
  declare title: string;
  declare message: string;
  declare isRead: boolean;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;
}

Notification.init(
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
    type: {
      type: DataTypes.ENUM(
        "HUMAN_TASK_CREATED",
        "AGENT_ERROR",
        "PERFORMANCE_ALERT",
        "SYSTEM",
      ),
      allowNull: false,
    },
    title: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    message: {
      type: DataTypes.TEXT,
      allowNull: false,
    },
    isRead: {
      type: DataTypes.BOOLEAN,
      defaultValue: false,
      field: "is_read",
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
    tableName: "notifications",
    indexes: [{ fields: ["user_id"] }, { fields: ["type"] }],
    defaultScope: { where: { isDeleted: false } },
  },
);
