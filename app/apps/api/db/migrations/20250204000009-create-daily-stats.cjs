'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('daily_stats', {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.UUIDV4,
        primaryKey: true,
      },
      agent_id: {
        type: Sequelize.UUID,
        allowNull: false,
        references: { model: 'agents', key: 'id' },
        onUpdate: 'CASCADE',
        onDelete: 'RESTRICT',
      },
      date: {
        type: Sequelize.DATEONLY,
        allowNull: false,
      },
      total_queries: {
        type: Sequelize.INTEGER,
        allowNull: false,
      },
      total_tokens: {
        type: Sequelize.INTEGER,
        allowNull: false,
      },
      avg_efficiency: {
        type: Sequelize.FLOAT,
        allowNull: true,
      },
      avg_quality: {
        type: Sequelize.FLOAT,
        allowNull: true,
      },
      created_at: {
        type: Sequelize.DATE,
        allowNull: false,
      },
      updated_at: {
        type: Sequelize.DATE,
        allowNull: false,
      },
      is_deleted: {
        type: Sequelize.BOOLEAN,
        defaultValue: false,
      },
      deleted_at: {
        type: Sequelize.DATE,
        allowNull: true,
      },
    });
    await queryInterface.addIndex('daily_stats', ['agent_id', 'date'], {
      unique: true,
      name: 'daily_stats_agent_id_date_key',
    });
  },

  async down(queryInterface) {
    await queryInterface.dropTable('daily_stats');
  },
};
