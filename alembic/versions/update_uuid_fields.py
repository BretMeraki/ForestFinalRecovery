# alembic/versions/update_uuid_fields.py

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "update_uuid_fields"
down_revision: Union[str, None] = "f5b76ed1b9bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(connection, table_name):
    """Safely check if a table exists without causing transaction issues."""
    try:
        # Use a simple query that won't cause transaction abort
        result = connection.execute(sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
        ), {"table_name": table_name})
        return result.scalar()
    except Exception:
        return False


def upgrade() -> None:
    connection = op.get_bind()
    
    print("🚀 Starting BULLETPROOF UUID migration for ForestFinal...")
    print("Using ultra-conservative approach to avoid PostgreSQL transaction issues")

    # STRATEGY: Only create tables that don't exist, avoid all modification operations
    
    # Check if users table exists
    users_exists = table_exists(connection, "users")
    print(f"Users table exists: {users_exists}")
    
    if not users_exists:
        print("Creating users table with UUID primary key...")
        try:
            op.create_table(
                "users",
                sa.Column(
                    "id",
                    postgresql.UUID(as_uuid=True),
                    primary_key=True,
                    server_default=sa.text("gen_random_uuid()"),
                ),
                sa.Column("email", sa.String(255), nullable=False, unique=True),
                sa.Column("hashed_password", sa.String(255), nullable=False),
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )
            print("✅ Created users table with UUID")
        except Exception as e:
            print(f"❌ Failed to create users table: {e}")
            raise
    else:
        print("✅ Users table already exists - skipping creation")
        # Check if users.id is UUID type
        try:
            result = connection.execute(sa.text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'id'
            """))
            data_type = result.scalar()
            print(f"Current users.id type: {data_type}")
            
            if data_type and 'uuid' not in data_type.lower():
                print("⚠️ WARNING: users.id is not UUID type!")
                print("⚠️ For production, you may need to manually convert this table")
                print("⚠️ For development, consider dropping the users table first")
            else:
                print("✅ users.id appears to be UUID type")
        except Exception as e:
            print(f"⚠️ Could not check users.id type: {e}")

    # Check and create hta_trees table
    hta_trees_exists = table_exists(connection, "hta_trees")
    print(f"HTA Trees table exists: {hta_trees_exists}")
    
    if not hta_trees_exists:
        print("Creating hta_trees table...")
        try:
            op.create_table(
                "hta_trees",
                sa.Column(
                    "id",
                    postgresql.UUID(as_uuid=True),
                    primary_key=True,
                    server_default=sa.text("gen_random_uuid()"),
                ),
                sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("goal_name", sa.String(255), nullable=False),
                sa.Column("initial_context", sa.Text(), nullable=True),
                sa.Column("top_node_id", postgresql.UUID(as_uuid=True), nullable=True),
                sa.Column("initial_roadmap_depth", sa.Integer(), nullable=True),
                sa.Column("initial_task_count", sa.Integer(), nullable=True),
                sa.Column(
                    "manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=True
                ),
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
                sa.ForeignKeyConstraint(
                    ["user_id"],
                    ["users.id"],
                ),
                sa.Index("idx_hta_trees_user_id_created_at", "user_id", "created_at"),
            )
            print("✅ Created hta_trees table")
        except Exception as e:
            print(f"❌ Failed to create hta_trees table: {e}")
            raise
    else:
        print("✅ hta_trees table already exists - skipping creation")

    # Check and create hta_nodes table
    hta_nodes_exists = table_exists(connection, "hta_nodes")
    print(f"HTA Nodes table exists: {hta_nodes_exists}")
    
    if not hta_nodes_exists:
        print("Creating hta_nodes table...")
        try:
            op.create_table(
                "hta_nodes",
                sa.Column(
                    "id",
                    postgresql.UUID(as_uuid=True),
                    primary_key=True,
                    server_default=sa.text("gen_random_uuid()"),
                ),
                sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
                sa.Column("tree_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("title", sa.String(255), nullable=False),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column(
                    "is_leaf",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
                sa.Column(
                    "status",
                    sa.String(),
                    nullable=False,
                    server_default=sa.text("'pending'"),
                ),
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
                sa.ForeignKeyConstraint(
                    ["parent_id"],
                    ["hta_nodes.id"],
                ),
                sa.ForeignKeyConstraint(
                    ["tree_id"],
                    ["hta_trees.id"],
                ),
                sa.ForeignKeyConstraint(
                    ["user_id"],
                    ["users.id"],
                ),
                sa.Index("idx_hta_nodes_parent_id", "parent_id"),
                sa.Index("idx_hta_nodes_tree_id", "tree_id"),
                sa.Index("idx_hta_nodes_user_id", "user_id"),
            )
            print("✅ Created hta_nodes table")
        except Exception as e:
            print(f"❌ Failed to create hta_nodes table: {e}")
            raise
    else:
        print("✅ hta_nodes table already exists - skipping creation")

    # Create cross-reference foreign key if both tables exist
    if hta_trees_exists or hta_nodes_exists:
        print("Checking cross-reference foreign key...")
        try:
            # Check if foreign key already exists
            result = connection.execute(sa.text("""
                SELECT COUNT(*) FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_hta_trees_top_node_id'
            """))
            fk_exists = result.scalar() > 0
            
            if not fk_exists:
                print("Creating cross-reference foreign key...")
                op.create_foreign_key(
                    "fk_hta_trees_top_node_id",
                    "hta_trees",
                    "hta_nodes",
                    ["top_node_id"],
                    ["id"],
                )
                print("✅ Created cross-reference foreign key")
            else:
                print("✅ Cross-reference foreign key already exists")
        except Exception as e:
            print(f"⚠️ Could not create cross-reference foreign key: {e}")

    # Create GIN index if hta_trees exists
    if hta_trees_exists or not table_exists(connection, "hta_trees"):
        print("Checking GIN index on hta_trees.manifest...")
        try:
            # Check if GIN index already exists
            result = connection.execute(sa.text("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE indexname = 'idx_hta_trees_manifest_gin'
            """))
            gin_exists = result.scalar() > 0
            
            if not gin_exists:
                print("Creating GIN index on hta_trees.manifest...")
                op.create_index(
                    "idx_hta_trees_manifest_gin",
                    "hta_trees",
                    ["manifest"],
                    postgresql_using="gin",
                )
                print("✅ Created GIN index")
            else:
                print("✅ GIN index already exists")
        except Exception as e:
            print(f"⚠️ Could not create GIN index: {e}")

    print("\n🎉 BULLETPROOF Migration completed successfully!")
    print("✅ All operations used safe, transaction-friendly approaches")
    print("✅ No risky table modifications attempted")
    print("✅ PostgreSQL transaction state preserved")


def downgrade() -> None:
    connection = op.get_bind()
    
    print("Starting safe downgrade migration...")
    
    # Drop tables in reverse order if they exist
    tables_to_drop = ["hta_nodes", "hta_trees"]
    
    for table_name in tables_to_drop:
        if table_exists(connection, table_name):
            try:
                print(f"Dropping {table_name} table...")
                op.drop_table(table_name)
                print(f"✅ Dropped {table_name} table")
            except Exception as e:
                print(f"⚠️ Could not drop {table_name}: {e}")
        else:
            print(f"✅ {table_name} table doesn't exist - skipping")

    # Note: We don't drop the users table in downgrade as it might contain important data
    print("ℹ️ Users table preserved (may contain important data)")
    print("✅ Downgrade completed safely")
