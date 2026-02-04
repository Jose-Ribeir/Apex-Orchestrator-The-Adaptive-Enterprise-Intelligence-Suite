'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('model_queries', {
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
      user_query: {
        type: Sequelize.TEXT,
        allowNull: false,
      },
      model_response: {
        type: Sequelize.TEXT,
        allowNull: true,
      },
      method_used: {
        type: Sequelize.ENUM('PERFORMANCE', 'EFFICIENCY'),
        allowNull: false,
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
    await queryInterface.addIndex('model_queries', ['agent_id']);
  },

  async down(queryInterface) {
    await queryInterface.dropTable('model_queries');
    await queryInterface.sequelize.query('DROP TYPE IF EXISTS "enum_model_queries_method_used";');
  },
};
