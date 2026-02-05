'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('human_tasks', {
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
      reason: {
        type: Sequelize.TEXT,
        allowNull: false,
      },
      retrieved_data: {
        type: Sequelize.TEXT,
        allowNull: true,
      },
      model_message: {
        type: Sequelize.TEXT,
        allowNull: false,
      },
      status: {
        type: Sequelize.ENUM('PENDING', 'RESOLVED'),
        allowNull: false,
        defaultValue: 'PENDING',
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
    await queryInterface.dropTable('human_tasks');
    await queryInterface.sequelize.query('DROP TYPE IF EXISTS "enum_human_tasks_status";');
  },
};
