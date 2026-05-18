from cassandra.cqlengine.models import Model
from cassandra.cqlengine import columns
import uuid
from datetime import datetime

def create_sessions_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'sessionsmodel',

        # Primary Key (id)
        'id': columns.UUID(primary_key=True, default=uuid.uuid4),

        # ID do contato (indexado para buscas)
        'contact_id': columns.UUID(index=True, required=True),

        'snapshot_id': columns.UUID(index=True, required=True),
    }

    return type('SessionsModel', (Model,), fields)

def create_snapshots_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'snapshotsmodel',

        # Primary Key (id)
        'id': columns.UUID(primary_key=True, default=uuid.uuid4),

        # ID do contato (indexado para buscas)
        'contact_id': columns.UUID(index=True, required=True),

        # Dados do snapshot
        'payload': columns.Map(columns.Text, columns.Text, default=dict),
        
        # Timestamp do snapshot
        'snapshot_timestamp': columns.DateTime(default=datetime.utcnow),
    }

    return type('SnapshotsModel', (Model,), fields)

def create_messages_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'messagesmodel',

        # Chave composta para otimização de leitura temporal
        'session_id': columns.UUID(partition_key=True, required=True),
        'message_timestamp': columns.DateTime(primary_key=True, clustering_order="ASC", default=datetime.utcnow),
        'reports_ids': columns.List(columns.UUID, default=list),

        # ID único da mensagem (não é PK mas pode ser útil como referência)
        'id': columns.UUID(default=uuid.uuid4, index=True),

        # Campos do Interaction (tipados corretamente)
        'contactIdentity': columns.Text(),
        'StatePreviousName': columns.Text(),
        'StatePreviousId': columns.Text(),
        'idWhereWas': columns.Text(),
        'nameStateWhereWas': columns.Text(),
        'stateName': columns.Text(),
        'stateId': columns.Text(),
        'blockId': columns.Text(),
        'BotName': columns.Text(),
        'Date': columns.DateTime(),
        'inputContent': columns.Text(required=True),
        'intentName': columns.Text(),
        'Latency': columns.Text(),
        'created_at': columns.DateTime(default=datetime.utcnow),
    }

    return type('MessagesModel', (Model,), fields)

def create_reports_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'reportsmodel',

        'id': columns.UUID(primary_key=True, default=uuid.uuid4,partition_key=True),

        'title': columns.Text(),
        'type': columns.Text(),

        'payload': columns.Map(columns.Text, columns.Text, default=dict),

        'created_at': columns.DateTime(default=datetime.utcnow),
    }

    return type('ReportsModel', (Model,), fields)

def create_active_message_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'activemessagemodel',

        # Primary Key
        'user_id': columns.Text(partition_key=True),  # exemplo: '5511910219259@wa.gw.msging.net'
        'datahora_envio': columns.DateTime(primary_key=True, clustering_order="DESC"),

        # Identificadores
        'id': columns.Text(index=True),  # 'activecampaign:e61b4e2d-...'
        'unique_id': columns.UUID(index=True),
        'bot_id': columns.Text(),

        # Template e estrutura
        'template_name': columns.Text(),
        'template_namespace': columns.Text(),
        'template_language_code': columns.Text(),
        'template_language_policy': columns.Text(),
        'components_body_parameters': columns.List(columns.Map(columns.Text, columns.Text)),
        'template_rendered_text': columns.Text(),  # exemplo: "Olá, *Silas*..."

        # Informações de envio
        'data': columns.Date(),  # '2025-05-01'
        'mes': columns.Text(),   # '2025-05'
        'type': columns.Text(),
        'category': columns.Text(),

        # Métricas
        'reception_time': columns.Double(),
        'consumption_time': columns.Double(),
        'answer_time': columns.Double(),

        # Resposta do usuário
        'resposta_usuario_type': columns.Text(),
        'resposta_usuario_value': columns.Text(),
        'resposta_usuario_direction': columns.Text(),  # 'sent', 'received' etc.


        'datahora_resposta_usuario': columns.DateTime(),

        # Status
        'received': columns.DateTime(),
        'consumed': columns.DateTime(),
        'failed': columns.Text(),
        'is_to_use_lite_api': columns.Boolean(),

        # Extras
        'responsible': columns.Text(),
        'client': columns.Text(),
        'unit_cost': columns.Double(),

        'created_at': columns.DateTime(default=datetime.utcnow),
    }

    return type('ActiveMessageModel', (Model,), fields)

def create_ticket_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'ticketmodel',

        # Primary Key composta: ticketId por ordenação de data
        'ticket_id': columns.UUID(partition_key=True),  # e6586852-3546-413c-ac5f-01941d4b7330
        'storage_date': columns.DateTime(primary_key=True, clustering_order="DESC"),

        # Identificadores
        'bot_id': columns.Text(),
        'sequential_id': columns.Integer(),
        'customer_identity': columns.Text(index=True),
        'agent_identity': columns.Text(),

        # Datas e status
        'status': columns.Text(),
        'open_date': columns.DateTime(),
        'first_response_date': columns.DateTime(),
        'close_date': columns.DateTime(),
        'expiration_date': columns.DateTime(),
        'team': columns.Text(),
        'closed': columns.Boolean(),

        # Meta-informações
        'tags': columns.List(columns.Text),
        'parent_sequential_id': columns.Integer(),
        'queue_time': columns.Text(),
        'first_response_time': columns.Text(),
        'average_agent_response_time': columns.Text(),
        'operational_time': columns.Text(),
        'ticket_total_time': columns.Text(),

        # Cliente
        'customer_name': columns.Text(),
        'customer_email': columns.Text(),
        'customer_gender': columns.Text(),
        'customer_city': columns.Text(),
        'customer_phone': columns.Text(),
        'customer_extras': columns.Map(columns.Text, columns.Text, default=dict),

        # Agente
        'agent_name': columns.Text(),
        'agent_email': columns.Text(),

        # Identificação original
        'original_customer_identity': columns.Text(),
        'original_bot_id': columns.Text(),

        # Controle
        'created_at': columns.DateTime(default=datetime.utcnow),
    }

    return type('TicketModel', (Model,), fields)

# ============================================================ VIEWS BY DATA ============================================================
def create_active_message_index_by_data_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'activemessagemodel_index_by_data',

        'data': columns.Date(partition_key=True),
        'mes': columns.Text(partition_key=True),  # exemplo: '2025-07'
        'user_id': columns.Text(primary_key=True),  # clustering ou full PK se `data` for muito granular
        'datahora_envio': columns.DateTime(),
        'unique_id': columns.UUID(index=True),
    }

    return type('ActiveMessageIndexByData', (Model,), fields)

def create_ticket_by_date_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'ticketmodel_by_date',

        # Chave primária focada em data
        'storage_day': columns.Date(partition_key=True),   # ex: 2025-07-28
        'ticket_id': columns.UUID(primary_key=True),       # para poder buscar no modelo original
        'storage_date': columns.DateTime(primary_key=True, clustering_order="DESC"),

        'open_date': columns.DateTime(),
        'close_date': columns.DateTime(),
        'created_at': columns.DateTime(),
    }

    return type('TicketByDateModel', (Model,), fields)
# ============================================================ END VIEWS BY DATA ============================================================
# ============================================================ BEGIN LOGGING ============================================================
def create_logs_model(keyspace: str):
    fields = {
        '__module__': __name__,
        '__keyspace__': keyspace,
        '__table_name__': 'loggingmodel',

        # Chave primária focada em data
        'storage_day': columns.Date(partition_key=True),   # ex: 2025-07-28
        'id': columns.UUID(primary_key=True),       # para poder buscar no modelo original
        'storage_date': columns.DateTime(primary_key=True, clustering_order="DESC"),

        'event': columns.Text(partition_key=True),
        'payload': columns.Text(),
    }

    return type('LoggingModel', (Model,), fields)