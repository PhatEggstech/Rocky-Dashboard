"""Inspect POS/WMS portal authorization metadata without reading secrets."""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
load_dotenv(os.environ['MCP_ENV_FILE'],override=True,encoding='utf-8-sig')
from mcp_server.tools import _get_pos_conn
from mcp_server.wms_tools import _get_wms_conn


def inspect(factory):
    with factory() as conn:
        conn.execute('BEGIN TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout='20s'")
        database=conn.execute('SELECT current_database()').fetchone()[0]
        matches=conn.execute('''SELECT table_schema,table_name,column_name,data_type
            FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema')
            AND (table_name ~* '(identity|aspnet|permission|privilege|access|role|claim|user|account|staff)'
                OR column_name ~* '(permission|privilege|role|claim|access|scope)')
            ORDER BY table_schema,table_name,ordinal_position''').fetchall()
        policies=conn.execute('SELECT schemaname,tablename,policyname,roles,cmd,qual,with_check FROM pg_policies').fetchall()
        rls=conn.execute('''SELECT n.nspname,c.relname,c.relrowsecurity,c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema')
            AND (c.relrowsecurity OR c.relforcerowsecurity)''').fetchall()
        return {'database':database,
            'candidate_columns':[dict(zip(('schema','table','column','type'),r)) for r in matches],
            'row_security_tables':[list(r) for r in rls],
            'row_security_policies':[list(r) for r in policies]}


def main():
    report={}
    for label,factory in [('POS',_get_pos_conn),('WMS',_get_wms_conn)]:
        try: report[label]=inspect(factory)
        except Exception as exc: report[label]={'error_type':type(exc).__name__}
    output=Path('C:/ProgramData/RockyMCP/config/employee-onboarding/portal-authorization-metadata-20261014.json')
    output.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    summary={label:{'database':r.get('database'),'candidate_tables':sorted({c['table'] for c in r.get('candidate_columns',[])}),
                   'rls_tables':len(r.get('row_security_tables',[])),'rls_policies':len(r.get('row_security_policies',[])),
                   'error_type':r.get('error_type')} for label,r in report.items()}
    print(json.dumps(summary))


if __name__=='__main__':main()
