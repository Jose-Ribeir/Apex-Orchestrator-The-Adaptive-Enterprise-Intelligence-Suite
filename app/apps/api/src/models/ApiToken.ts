import { Model, DataTypes, Optional } from "sequelize";
import { sequelize } from "../config/database";

export interface ApiTokenAttributes {
  id: string;
  userId: string;
  tokenHash: string;
  name: string | null;
  lastUsedAt: Date | null;
  expiresAt: Date | null;
  createdAt?: Date;
  updatedAt?: Date;
}

export type ApiTokenCreationAttributes = Optional<
  ApiTokenAttributes,
  "id" | "name" | "lastUsedAt" | "expiresAt" | "createdAt" | "updatedAt"
>;

export class ApiToken
  extends Model<ApiTokenAttributes, ApiTokenCreationAttributes>
  implements ApiTokenAttributes
{
  declare id: string;
  declare userId: string;
  declare tokenHash: string;
  declare name: string | null;
  declare lastUsedAt: Date | null;
  declare expiresAt: Date | null;
  declare readonly createdAt: Date;
  declare readonly updatedAt: Date;
}

ApiToken.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    userId: {
      type: DataTypes.TEXT,
      allowNull: false,
      field: "user_id",
    },
    tokenHash: {
      type: DataTypes.TEXT,
      allowNull: false,
      field: "token_hash",
    },
    name: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    lastUsedAt: {
      type: DataTypes.DATE,
      allowNull: true,
      field: "last_used_at",
    },
    expiresAt: {
      type: DataTypes.DATE,
      allowNull: true,
      field: "expires_at",
    },
  },
  {
    sequelize,
    tableName: "api_tokens",
    defaultScope: {},
    indexes: [{ fields: ["token_hash"] }, { fields: ["user_id"] }],
  },
);
