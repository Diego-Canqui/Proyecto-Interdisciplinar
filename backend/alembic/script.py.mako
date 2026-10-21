<%inherit file="app:-1"/>

<%!
import re

def render_item(type_, obj, autogen_context):
    return False
%>

<%block name="header">
${imports}
from alembic import op
import sqlalchemy as sa
</%block>

<%block name="content">
${upgs}
${downgrades}
</%block>
