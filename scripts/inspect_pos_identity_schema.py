"""Inspect authorization metadata only; never read credential column values."""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from mcp_server.tools import _get_pos_conn


def main():
    with _get_pos_conn() as conn:
        conn.execute('BEGIN TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout = '20s'")
        database=conn.execute('SELECT current_database(),current_user').fetchone()
        tables=conn.execute('''SELECT table_schema,table_name,table_type FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog','information_schema')
            AND (table_name ILIKE '%identity%' OR table_name ILIKE '%aspnet%'
                OR table_name ILIKE '%permission%' OR table_name ILIKE '%role%'
                OR table_name IN ('Staff','Account')) ORDER BY table_schema,table_name''').fetchall()
        details=[]
        for schema,name,kind in tables:
            columns=conn.execute('''SELECT column_name,data_type,udt_name,is_nullable,
                character_maximum_length,column_default FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position''',[schema,name]).fetchall()
            constraints=conn.execute('''SELECT con.conname,con.contype,pg_get_constraintdef(con.oid)
                FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s
                ORDER BY con.conname''',[schema,name]).fetchall()
            inbound=conn.execute('''SELECT n.nspname,c.relname,con.conname,pg_get_constraintdef(con.oid)
                FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
                JOIN pg_namespace n ON n.oid=c.relnamespace
                JOIN pg_class target ON target.oid=con.confrelid
                JOIN pg_namespace tn ON tn.oid=target.relnamespace
                WHERE con.contype='f' AND tn.nspname=%s AND target.relname=%s
                ORDER BY n.nspname,c.relname''',[schema,name]).fetchall()
            details.append({'schema':schema,'table':name,'type':kind,
                'columns':[dict(zip(('name','type','udt','nullable','max_length','default'),r)) for r in columns],
                'constraints':[dict(zip(('name','type','definition'),r)) for r in constraints],
                'referenced_by':[dict(zip(('schema','table','constraint','definition'),r)) for r in inbound]})
        roles=conn.execute('''SELECT "RoleCode",COUNT(*) FROM "Account"
            WHERE "DeleteAt" IS NULL GROUP BY "RoleCode" ORDER BY "RoleCode"''').fetchall()
    report={'database':database[0],'credential_values_read':False,'tables':details,
            'account_role_counts':[{'role_code':r[0],'count':r[1]} for r in roles]}
    path=Path('C:/ProgramData/RockyMCP/config/employee-onboarding/pos-identity-schema-20261014.json')
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    print(json.dumps({'database':database[0],'tables':[{'schema':r['schema'],'table':r['table'],'columns':len(r['columns'])} for r in details],
                      'account_role_counts':report['account_role_counts'],'credential_values_read':False},ensure_ascii=True))


if __name__=='__main__':main()
