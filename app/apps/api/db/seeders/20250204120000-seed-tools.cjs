'use strict';

const { v4: uuidv4 } = require('uuid');

const TOOL_NAMES = [
  'RAG',
  'Chain-of-Thought (CoT)',
  'Straight Model',
  'Web Search',
];

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface) {
    const now = new Date();
    for (const name of TOOL_NAMES) {
      await queryInterface.sequelize.query(
        `INSERT INTO tools (id, name, created_at, updated_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT (name) DO NOTHING`,
        {
          replacements: [uuidv4(), name, now, now],
        }
      );
    }
  },

  async down(queryInterface) {
    await queryInterface.bulkDelete('tools', {
      name: TOOL_NAMES,
    });
  },
};
