'use strict';

const bcrypt = require('bcrypt');
const { randomUUID } = require('crypto');

const DEFAULT_ADMIN_EMAIL = 'admin@geminimesh.com';
const DEFAULT_ADMIN_NAME = 'Truste Route Admin';
const DEFAULT_ADMIN_PASSWORD = process.env.SEED_ADMIN_PASSWORD;

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface) {
    const existing = await queryInterface.sequelize.query(
      `SELECT "id" FROM "user" WHERE "email" = $1`,
      { bind: [DEFAULT_ADMIN_EMAIL], type: queryInterface.sequelize.QueryTypes.SELECT }
    );

    if (existing.length > 0) {
      await queryInterface.sequelize.query(
        `DELETE FROM "account" WHERE "userId" = $1`,
        { bind: [existing[0].id] }
      );
      await queryInterface.sequelize.query(
        `DELETE FROM "user" WHERE "email" = $1`,
        { bind: [DEFAULT_ADMIN_EMAIL] }
      );
    }

    const userId = randomUUID();
    const accountId = randomUUID();
    const now = new Date().toISOString();
    const passwordHash = await bcrypt.hash(DEFAULT_ADMIN_PASSWORD, 10);

    // Use bind ($1, $2, ...) so the bcrypt hash is sent as a parameter, not interpolated
    await queryInterface.sequelize.query(
      `INSERT INTO "user" ("id", "name", "email", "emailVerified", "image", "createdAt", "updatedAt")
       VALUES ($1, $2, $3, true, NULL, $4::timestamptz, $5::timestamptz)`,
      { bind: [userId, DEFAULT_ADMIN_NAME, DEFAULT_ADMIN_EMAIL, now, now] }
    );

    await queryInterface.sequelize.query(
      `INSERT INTO "account" ("id", "userId", "accountId", "providerId", "password", "createdAt", "updatedAt")
       VALUES ($1, $2, $3, 'credential', $4, $5::timestamptz, $6::timestamptz)`,
      { bind: [accountId, userId, DEFAULT_ADMIN_EMAIL, passwordHash, now, now] }
    );
  },

  async down(queryInterface) {
    await queryInterface.sequelize.query(
      `DELETE FROM "account" WHERE "userId" IN (SELECT "id" FROM "user" WHERE "email" = $1)`,
      { bind: [DEFAULT_ADMIN_EMAIL] }
    );
    await queryInterface.sequelize.query(
      `DELETE FROM "user" WHERE "email" = $1`,
      { bind: [DEFAULT_ADMIN_EMAIL] }
    );
  },
};
