import { Model, DataTypes, Optional } from "sequelize";
import { sequelize } from "../config/database";

export interface ToolAttributes {
  id: string;
  name: string;
  createdAt?: Date;
  updatedAt?: Date;
  isDeleted?: boolean;
  deletedAt?: Date | null;
}

export type ToolCreationAttributes = Optional<
  ToolAttributes,
  "id" | "createdAt" | "updatedAt" | "isDeleted" | "deletedAt"
>;

export class Tool
  extends Model<ToolAttributes, ToolCreationAttributes>
  implements ToolAttributes
{
  declare id: string;
  declare name: string;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
  declare isDeleted: boolean;
  declare deletedAt: Date | null;
}

Tool.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING,
      allowNull: false,
      unique: true,
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
    tableName: "tools",
    defaultScope: { where: { isDeleted: false } },
  },
);
