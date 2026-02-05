'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('agent_tools', {
      agent_id: {
        type: Sequelize.UUID,
        allowNull: false,
        references: { model: 'agents', key: 'id' },
        onUpdate: 'CASCADE',
        onDelete: 'CASCADE',
      },
      tool_id: {
        type: Sequelize.UUID,
        allowNull: false,
        references: { model: 'tools', key: 'id' },
        onUpdate: 'CASCADE',
        onDelete: 'CASCADE',
      },
      created_at: {
        type: Sequelize.DATE,
        allowNull: false,
      },
    });
    await queryInterface.addConstraint('agent_tools', {
      fields: ['agent_id', 'tool_id'],
      type: 'primary key',
      name: 'agent_tools_pkey',
    });
  },

  async down(queryInterface) {
    await queryInterface.dropTable('agent_tools');
  },
};
