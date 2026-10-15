"""Analyzer 7: Database and Migration Analyzer.

Inspects SQLAlchemy ORM models, Alembic migrations, and SQL schemas.
Detects model/schema mismatches, dropped or renamed columns, risky type changes,
missing migrations, foreign-key/cascade hazards, and synthesizes safe migration plans.
"""

import ast
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzers.base import BaseAnalyzer
from app.analysis.indexer import build_repository_index


class DatabaseMigrationAnalyzer(BaseAnalyzer):
    name = "database_migration"
    version = "1.0.0"
    description = "Inspects SQLAlchemy models, Alembic migrations, and SQL schemas for drift and migration hazards."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if not index:
            index = build_repository_index(repo_dir, commit_sha)

        models: List[Dict[str, Any]] = []
        migrations: List[Dict[str, Any]] = []
        sql_schemas: List[Dict[str, Any]] = []
        findings: List[Dict[str, Any]] = []
        limitations: List[str] = []

        files_scanned = 0

        # 1. Inspect Python files for SQLAlchemy ORM models and Alembic migrations
        for root, dirs, fnames in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".pytest_cache"]]
            for fn in fnames:
                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, repo_dir).replace("\\", "/")

                if fn.endswith(".py"):
                    files_scanned += 1
                    # Alembic migration versions
                    if "versions" in rel_p or "migration" in rel_p.lower():
                        mig_info = self._parse_alembic_migration(full_p, rel_p)
                        if mig_info:
                            migrations.append(mig_info)
                    
                    # SQLAlchemy Models
                    detected_models = self._parse_sqlalchemy_models(full_p, rel_p)
                    models.extend(detected_models)

                elif fn.endswith(".sql"):
                    files_scanned += 1
                    sql_info = self._parse_sql_file(full_p, rel_p)
                    if sql_info:
                        sql_schemas.append(sql_info)

        # 2. Check for Dropped/Renamed Columns in Migrations and SQL Schemas
        dropped_col_hazards = self._check_dropped_columns(migrations, sql_schemas)
        findings.extend(dropped_col_hazards)

        # 3. Check for Risky Type Changes and NOT NULL additions without default
        risky_type_hazards = self._check_risky_type_changes(migrations, models)
        findings.extend(risky_type_hazards)

        # 4. Check for Foreign Key and Cascade Hazards in Models
        fk_hazards = self._check_foreign_key_hazards(models)
        findings.extend(fk_hazards)

        # 5. Check for Missing Migrations and Model/Schema Mismatches
        missing_migrations = self._check_missing_migrations(models, migrations, sql_schemas)
        findings.extend(missing_migrations)

        if not models:
            limitations.append("No SQLAlchemy ORM models detected in repository Python source files.")
        if not migrations and not sql_schemas:
            limitations.append("No Alembic migration versions or SQL schema definition files detected.")

        safe_migration_plan = self._generate_safe_migration_guidelines(findings)

        summary = (
            f"Analyzed {len(models)} SQLAlchemy ORM model(s), {len(migrations)} Alembic migration(s), "
            f"and {len(sql_schemas)} SQL schema file(s). Discovered {len(findings)} database hazard(s) and drift issue(s)."
        )

        details = {
            "models_count": len(models),
            "models": models[:30],
            "migrations_count": len(migrations),
            "migrations": migrations[:30],
            "sql_schemas_count": len(sql_schemas),
            "findings_count": len(findings),
            "safe_migration_plan": safe_migration_plan,
        }

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL" if (models or migrations or sql_schemas) else "PARTIAL",
            "files_analyzed": files_scanned,
            "summary": summary,
            "findings_count": len(findings),
            "findings": findings,
            "details": details,
            "limitations": limitations,
        }

    def _parse_sqlalchemy_models(self, file_path: str, rel_path: str) -> List[Dict[str, Any]]:
        """Parses SQLAlchemy ORM models from Python source files."""
        models: List[Dict[str, Any]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return models

        # Fast check if file looks like SQLAlchemy model
        if "Base" not in content and "__tablename__" not in content and "Column" not in content:
            return models

        try:
            tree = ast.parse(content, filename=file_path)
        except Exception:
            # Fallback regex
            return self._parse_models_regex(content, rel_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_model = False
                for base in node.bases:
                    base_id = ""
                    if isinstance(base, ast.Name):
                        base_id = base.id
                    elif isinstance(base, ast.Attribute):
                        base_id = base.attr
                    if base_id in ["Base", "Model", "db", "DeclarativeBase"]:
                        is_model = True

                table_name = None
                columns: List[Dict[str, Any]] = []

                for item in node.body:
                    # Check __tablename__
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "__tablename__":
                                if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                                    table_name = item.value.value
                                    is_model = True

                    # Check Column definitions or mapped_column
                    col_info = self._parse_ast_column(item)
                    if col_info:
                        columns.append(col_info)
                        is_model = True

                if is_model:
                    models.append({
                        "name": node.name,
                        "table_name": table_name or node.name.lower(),
                        "file": rel_path,
                        "line": node.lineno,
                        "columns": columns,
                    })

        return models

    def _parse_ast_column(self, item: ast.AST) -> Optional[Dict[str, Any]]:
        """Extracts column attributes from an AST Assign or AnnAssign statement."""
        col_name = None
        call_node: Optional[ast.Call] = None

        if isinstance(item, ast.Assign):
            if item.targets and isinstance(item.targets[0], ast.Name):
                col_name = item.targets[0].id
            if isinstance(item.value, ast.Call):
                call_node = item.value
        elif isinstance(item, ast.AnnAssign):
            if isinstance(item.target, ast.Name):
                col_name = item.target.id
            if isinstance(item.value, ast.Call):
                call_node = item.value

        if not col_name or not call_node:
            return None

        # Check if Column(...) or mapped_column(...)
        func_name = ""
        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            func_name = call_node.func.attr

        if func_name not in ["Column", "mapped_column"]:
            return None

        col_type = "Unknown"
        primary_key = False
        nullable = True
        has_default = False
        has_index = False
        foreign_key = None

        # Check positional args for Type or ForeignKey
        for arg in call_node.args:
            if isinstance(arg, ast.Name):
                if arg.id in ["Integer", "String", "Text", "Boolean", "DateTime", "Float", "Numeric", "UUID"]:
                    col_type = arg.id
            elif isinstance(arg, ast.Call):
                if isinstance(arg.func, (ast.Name, ast.Attribute)):
                    fname = arg.func.id if isinstance(arg.func, ast.Name) else arg.func.attr
                    if fname == "ForeignKey":
                        fk_target = ""
                        ondelete = None
                        if arg.args and isinstance(arg.args[0], ast.Constant):
                            fk_target = str(arg.args[0].value)
                        for kw in arg.keywords:
                            if kw.arg == "ondelete" and isinstance(kw.value, ast.Constant):
                                ondelete = str(kw.value.value).upper()
                        foreign_key = {"target": fk_target, "ondelete": ondelete}
                    elif fname in ["String", "Integer", "Numeric", "Enum"]:
                        col_type = fname

        # Check keyword arguments
        for kw in call_node.keywords:
            if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant):
                primary_key = bool(kw.value.value)
                if primary_key:
                    nullable = False
            elif kw.arg == "nullable" and isinstance(kw.value, ast.Constant):
                nullable = bool(kw.value.value)
            elif kw.arg in ["default", "server_default"]:
                has_default = True
            elif kw.arg == "index" and isinstance(kw.value, ast.Constant):
                has_index = bool(kw.value.value)

        return {
            "name": col_name,
            "type": col_type,
            "primary_key": primary_key,
            "nullable": nullable,
            "has_default": has_default,
            "has_index": has_index,
            "foreign_key": foreign_key,
            "line": getattr(item, "lineno", 1),
        }

    def _parse_models_regex(self, content: str, rel_path: str) -> List[Dict[str, Any]]:
        """Fallback regex parsing for models."""
        models = []
        cls_re = re.compile(r"class\s+([A-Za-z0-9_]+)\s*\((?:Base|models\.Model|db\.Model)\):")
        tbl_re = re.compile(r"""__tablename__\s*=\s*["']([^"']+)["']""")
        for m in cls_re.finditer(content):
            cls_name = m.group(1)
            line_no = content[: m.start()].count("\n") + 1
            sub = content[m.start() : m.start() + 500]
            tbl_m = tbl_re.search(sub)
            tbl_name = tbl_m.group(1) if tbl_m else cls_name.lower()
            models.append({
                "name": cls_name,
                "table_name": tbl_name,
                "file": rel_path,
                "line": line_no,
                "columns": [],
            })
        return models

    def _parse_alembic_migration(self, file_path: str, rel_path: str) -> Optional[Dict[str, Any]]:
        """Parses Alembic migration script for upgrade operations."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return None

        # Fast check if file is an Alembic migration
        if "revision" not in content and "upgrade" not in content:
            return None

        rev_m = re.search(r"""revision\s*(?::\s*str)?\s*=\s*['"]([^'"]+)['"]""", content)
        down_rev_m = re.search(r"""down_revision\s*(?::\s*Union\[str,\s*None\])?\s*=\s*['"]?([^'"]+)['"]?""", content)

        rev_id = rev_m.group(1) if rev_m else os.path.basename(file_path)
        down_rev = down_rev_m.group(1) if down_rev_m else None

        operations: List[Dict[str, Any]] = []

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            # op.drop_column('table', 'column')
            drop_col = re.search(r"""op\.drop_column\s*\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]""", line)
            if drop_col:
                operations.append({
                    "type": "drop_column",
                    "table": drop_col.group(1),
                    "column": drop_col.group(2),
                    "line": idx,
                    "raw": line.strip(),
                })

            # op.alter_column('table', 'col', nullable=False)
            alter_col = re.search(r"""op\.alter_column\s*\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]""", line)
            if alter_col:
                is_non_nullable = "nullable=False" in line
                type_change = "type_=" in line
                operations.append({
                    "type": "alter_column",
                    "table": alter_col.group(1),
                    "column": alter_col.group(2),
                    "is_non_nullable": is_non_nullable,
                    "type_change": type_change,
                    "line": idx,
                    "raw": line.strip(),
                })

            # op.add_column('table', sa.Column('col', ...))
            add_col = re.search(r"""op\.add_column\s*\(\s*['"]([^'"]+)['"]""", line)
            if add_col:
                is_non_nullable = "nullable=False" in line and "server_default" not in line
                operations.append({
                    "type": "add_column",
                    "table": add_col.group(1),
                    "is_non_nullable": is_non_nullable,
                    "line": idx,
                    "raw": line.strip(),
                })

            # op.drop_table('table')
            drop_tbl = re.search(r"""op\.drop_table\s*\(\s*['"]([^'"]+)['"]""", line)
            if drop_tbl:
                operations.append({
                    "type": "drop_table",
                    "table": drop_tbl.group(1),
                    "line": idx,
                    "raw": line.strip(),
                })

            # op.create_table('table', ...)
            create_tbl = re.search(r"""op\.create_table\s*\(\s*['"]([^'"]+)['"]""", line)
            if create_tbl:
                operations.append({
                    "type": "create_table",
                    "table": create_tbl.group(1),
                    "line": idx,
                    "raw": line.strip(),
                })

        return {
            "revision": rev_id,
            "down_revision": down_rev,
            "file": rel_path,
            "operations": operations,
        }

    def _parse_sql_file(self, file_path: str, rel_path: str) -> Optional[Dict[str, Any]]:
        """Extracts schema definitions and destructive queries from SQL files."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return None

        tables: List[str] = []
        destructive_ops: List[Dict[str, Any]] = []

        create_tbl_re = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)", re.IGNORECASE)
        drop_col_re = re.compile(r"ALTER\s+TABLE\s+([a-zA-Z0-9_]+)\s+DROP\s+COLUMN\s+([a-zA-Z0-9_]+)", re.IGNORECASE)

        for match in create_tbl_re.finditer(content):
            tables.append(match.group(1))

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            m = drop_col_re.search(line)
            if m:
                destructive_ops.append({
                    "type": "drop_column",
                    "table": m.group(1),
                    "column": m.group(2),
                    "line": idx,
                })

        return {
            "file": rel_path,
            "tables": tables,
            "destructive_ops": destructive_ops,
        }

    def _check_dropped_columns(
        self, migrations: List[Dict[str, Any]], sql_schemas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identifies dropped column hazards in migrations and SQL files."""
        hazards = []
        for mig in migrations:
            for op in mig.get("operations", []):
                if op["type"] == "drop_column":
                    hazards.append({
                        "rule_id": "DB-HAZARD-DROPPED-COL",
                        "category": "Database",
                        "severity": "Critical",
                        "confidence": "High",
                        "classification": "Definite breaking database migration hazard",
                        "file_path": mig["file"],
                        "line_number": op["line"],
                        "title": f"Dangerous Dropped Column: `{op['table']}.{op['column']}`",
                        "description": (
                            f"Migration drops column `{op['column']}` on table `{op['table']}`. "
                            f"In rolling deployments, active application instances running previous code will crash "
                            f"with 'column does not exist' runtime errors."
                        ),
                        "evidence": op["raw"],
                        "remediation": (
                            f"Follow expand-contract: (1) Deprecate and remove code references to `{op['column']}`, "
                            f"(2) Deploy application, (3) Drop `{op['column']}` in a separate subsequent deployment."
                        ),
                    })
                elif op["type"] == "drop_table":
                    hazards.append({
                        "rule_id": "DB-HAZARD-DROPPED-TABLE",
                        "category": "Database",
                        "severity": "High",
                        "confidence": "High",
                        "classification": "Definite breaking database migration hazard",
                        "file_path": mig["file"],
                        "line_number": op["line"],
                        "title": f"Destructive Dropped Table: `{op['table']}`",
                        "description": f"Migration completely drops table `{op['table']}`, risking permanent data loss.",
                        "evidence": op["raw"],
                        "remediation": "Confirm table is fully retired and backup schema before running table drop.",
                    })

        for sql in sql_schemas:
            for op in sql.get("destructive_ops", []):
                hazards.append({
                    "rule_id": "DB-HAZARD-DROPPED-COL",
                    "category": "Database",
                    "severity": "Critical",
                    "confidence": "High",
                    "classification": "Definite breaking database migration hazard",
                    "file_path": sql["file"],
                    "line_number": op["line"],
                    "title": f"SQL Schema Drops Column: `{op['table']}.{op['column']}`",
                    "description": f"Direct ALTER TABLE DROP COLUMN statement detected for `{op['table']}.{op['column']}`.",
                    "evidence": f"Line {op['line']} in {sql['file']}",
                    "remediation": "Deprecate column usage in application code before running destructive ALTER TABLE.",
                })

        return hazards

    def _check_risky_type_changes(
        self, migrations: List[Dict[str, Any]], models: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identifies risky type changes and non-nullable column additions without default."""
        hazards = []
        for mig in migrations:
            for op in mig.get("operations", []):
                if op["type"] == "add_column" and op.get("is_non_nullable"):
                    hazards.append({
                        "rule_id": "DB-HAZARD-NOT-NULL-ADD",
                        "category": "Database",
                        "severity": "High",
                        "confidence": "High",
                        "classification": "Definite breaking database migration hazard",
                        "file_path": mig["file"],
                        "line_number": op["line"],
                        "title": f"NOT NULL Column Added Without Default on `{op['table']}`",
                        "description": (
                            f"Adding a non-nullable column to table `{op['table']}` without a `server_default` "
                            f"will fail if existing records exist in the table."
                        ),
                        "evidence": op["raw"],
                        "remediation": "Add column with nullable=True, backfill data, and alter to nullable=False in a follow-up step.",
                    })
                elif op["type"] == "alter_column" and (op.get("is_non_nullable") or op.get("type_change")):
                    hazards.append({
                        "rule_id": "DB-HAZARD-RISKY-ALTER",
                        "category": "Database",
                        "severity": "High",
                        "confidence": "Medium",
                        "classification": "Valid heuristic finding requiring manual verification",
                        "file_path": mig["file"],
                        "line_number": op["line"],
                        "title": f"Risky Alter Column Operation on `{op['table']}.{op['column']}`",
                        "description": f"Altering column type or nullability on `{op['table']}.{op['column']}` risks table lock contention or data truncation.",
                        "evidence": op["raw"],
                        "remediation": "Ensure backfill script has completed and perform alteration during low-traffic maintenance window.",
                    })

        # Check ORM models for non-nullable columns without default (excluding primary keys)
        for model in models:
            for col in model.get("columns", []):
                if not col["nullable"] and not col["primary_key"] and not col["has_default"]:
                    hazards.append({
                        "rule_id": "DB-MODEL-NOT-NULL-NO-DEFAULT",
                        "category": "Database",
                        "severity": "Medium",
                        "confidence": "Medium",
                        "classification": "Valid heuristic finding requiring manual verification",
                        "file_path": model["file"],
                        "line_number": col["line"],
                        "title": f"Non-Nullable Column Without Default: `{model['name']}.{col['name']}`",
                        "description": (
                            f"Model `{model['name']}` column `{col['name']}` is defined with `nullable=False` "
                            f"without an explicit default value."
                        ),
                        "evidence": f"Column {col['name']} in {model['file']}:{col['line']}",
                        "remediation": "Provide default=... or server_default=... to prevent runtime insertion errors.",
                    })

        return hazards

    def _check_foreign_key_hazards(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flags unindexed foreign keys and dangerous cascading deletes."""
        hazards = []
        critical_tables = {"user", "users", "account", "accounts", "organization", "organizations", "tenant", "tenants"}

        for model in models:
            for col in model.get("columns", []):
                fk = col.get("foreign_key")
                if not fk:
                    continue

                # Check missing index on foreign key
                if not col.get("has_index") and not col.get("primary_key"):
                    hazards.append({
                        "rule_id": "DB-HAZARD-UNINDEXED-FK",
                        "category": "Database",
                        "severity": "Medium",
                        "confidence": "High",
                        "classification": "Definite performance defect",
                        "file_path": model["file"],
                        "line_number": col["line"],
                        "title": f"Unindexed Foreign Key: `{model['name']}.{col['name']}`",
                        "description": (
                            f"Foreign key `{model['name']}.{col['name']}` referencing `{fk['target']}` lacks an explicit index. "
                            f"This can trigger full table locks when deleting rows in the parent table."
                        ),
                        "evidence": f"ForeignKey('{fk['target']}') without index=True",
                        "remediation": f"Add `index=True` or `Index('ix_{model['table_name']}_{col['name']}', '{col['name']}')`.",
                    })

                # Check dangerous cascade deletes on critical tables
                target_table = fk.get("target", "").split(".")[0].lower()
                ondelete = fk.get("ondelete")
                if ondelete == "CASCADE" and target_table in critical_tables:
                    hazards.append({
                        "rule_id": "DB-HAZARD-DANGEROUS-CASCADE",
                        "category": "Database",
                        "severity": "High",
                        "confidence": "Medium",
                        "classification": "Valid heuristic finding requiring manual verification",
                        "file_path": model["file"],
                        "line_number": col["line"],
                        "title": f"Risky CASCADE Delete from Core Entity: `{model['name']}` -> `{fk['target']}`",
                        "description": (
                            f"Foreign key has `ondelete='CASCADE'` on high-value entity `{fk['target']}`. "
                            f"Deleting a parent record may recursively delete substantial business data."
                        ),
                        "evidence": f"ForeignKey('{fk['target']}', ondelete='CASCADE')",
                        "remediation": "Consider using `ondelete='RESTRICT'` or soft deletion flags instead of database-level cascade.",
                    })

        return hazards

    def _check_missing_migrations(
        self, models: List[Dict[str, Any]], migrations: List[Dict[str, Any]], sql_schemas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detects models that are absent from Alembic migrations or SQL schema tables."""
        hazards = []
        if not models:
            return hazards

        migrated_tables: Set[str] = set()
        for mig in migrations:
            for op in mig.get("operations", []):
                if op["type"] == "create_table":
                    migrated_tables.add(op["table"].lower())

        for sql in sql_schemas:
            for tbl in sql.get("tables", []):
                migrated_tables.add(tbl.lower())

        # If migrations exist, check for models whose tables have never been migrated
        if migrations or sql_schemas:
            for model in models:
                tbl = model["table_name"].lower()
                if tbl not in migrated_tables:
                    hazards.append({
                        "rule_id": "DB-MISSING-MIGRATION",
                        "category": "Database",
                        "severity": "High",
                        "confidence": "Medium",
                        "classification": "Valid heuristic finding requiring manual verification",
                        "file_path": model["file"],
                        "line_number": model["line"],
                        "title": f"Missing Migration for Model `{model['name']}` (Table `{model['table_name']}`)",
                        "description": (
                            f"ORM model `{model['name']}` maps to table `{model['table_name']}`, "
                            f"but no `op.create_table('{model['table_name']}')` was found in Alembic migrations or SQL files."
                        ),
                        "evidence": f"Model defined in {model['file']}:{model['line']}",
                        "remediation": f"Generate and apply an Alembic migration for `{model['table_name']}`.",
                    })
        elif models:
            # Models exist, but 0 migrations or SQL files exist in repository
            hazards.append({
                "rule_id": "DB-NO-MIGRATION-FRAMEWORK",
                "category": "Database",
                "severity": "Medium",
                "confidence": "High",
                "classification": "Definite project hygiene finding",
                "file_path": models[0]["file"],
                "line_number": models[0]["line"],
                "title": "No Database Migration Framework Configured",
                "description": (
                    f"Found {len(models)} SQLAlchemy ORM model(s) but no Alembic migration directory or SQL schemas. "
                    f"Schema evolution without automated migrations risks production drift."
                ),
                "evidence": f"{len(models)} models detected, 0 migrations found.",
                "remediation": "Initialize Alembic with `alembic init alembic` and version-control schema migrations.",
            })

        return hazards

    def _generate_safe_migration_guidelines(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesizes an expand-contract safe migration plan based on detected hazards."""
        steps = []
        has_dropped = any(f["rule_id"] == "DB-HAZARD-DROPPED-COL" for f in findings)
        has_not_null = any(f["rule_id"] == "DB-HAZARD-NOT-NULL-ADD" for f in findings)
        has_unindexed = any(f["rule_id"] == "DB-HAZARD-UNINDEXED-FK" for f in findings)

        if has_dropped:
            steps.append({
                "phase": "Expand (Phase 1)",
                "action": "Deprecate column in application code without deleting it from schema.",
            })
            steps.append({
                "phase": "Deploy (Phase 2)",
                "action": "Deploy code and verify all queries omit the deprecated column.",
            })
            steps.append({
                "phase": "Contract (Phase 3)",
                "action": "Apply Alembic migration to drop column after traffic has safely switched.",
            })

        if has_not_null:
            steps.append({
                "phase": "Expand",
                "action": "Add column with nullable=True (or valid server_default) in migration.",
            })
            steps.append({
                "phase": "Backfill",
                "action": "Run background asynchronous job to populate column on existing rows.",
            })
            steps.append({
                "phase": "Contract",
                "action": "Apply follow-up migration altering column to nullable=False.",
            })

        if has_unindexed:
            steps.append({
                "phase": "Performance",
                "action": "Add CONCURRENTLY index in migration to avoid locking parent and child tables during creation.",
            })

        if not steps:
            steps.append({
                "phase": "Standard",
                "action": "No destructive database schema operations detected. Standard forward migration is safe.",
            })

        return {
            "recommended_strategy": "Expand-Contract Pattern",
            "steps": steps,
        }
