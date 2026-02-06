'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface) {
    await queryInterface.sequelize.query(`
      DO $$
      BEGIN
        IF NOT EXISTS (
          SELECT 1 FROM pg_enum e
          JOIN pg_type t ON e.enumtypid = t.oid
          WHERE t.typname = 'enum_agents_mode' AND e.enumlabel = 'BALANCED'
        ) THEN
          ALTER TYPE enum_agents_mode ADD VALUE 'BALANCED';
        END IF;
      END
      $$;
    `);
  },

  async down() {
    // PostgreSQL does not support removing a value from an enum; would require recreating the type
    // and altering the column. No-op for safety.
  },
};
