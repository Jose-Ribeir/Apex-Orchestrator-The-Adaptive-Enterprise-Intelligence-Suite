'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('performance_metrics', {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.UUIDV4,
        primaryKey: true,
      },
      model_query_id: {
        type: Sequelize.UUID,
        allowNull: false,
        unique: true,
        references: { model: 'model_queries', key: 'id' },
        onUpdate: 'CASCADE',
        onDelete: 'CASCADE',
      },
      token_usage: {
        type: Sequelize.INTEGER,
        allowNull: false,
      },
      response_time_ms: {
        type: Sequelize.INTEGER,
        allowNull: true,
      },
      efficiency_score: {
        type: Sequelize.FLOAT,
        allowNull: true,
      },
      quality_score: {
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
  },

  async down(queryInterface) {
    await queryInterface.dropTable('performance_metrics');
  },
};
