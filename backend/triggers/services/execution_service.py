import uuid
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

from ..domain.entities import TriggerResult, TriggerEvent
from services.supabase import DBConnection
from services import redis
from utils.logger import logger, structlog
from run_agent_background import run_agent_background
from .workflow_parser import WorkflowParser, format_workflow_for_llm


class TriggerExecutionService:
    def __init__(self, db_connection: DBConnection):
        self._db = db_connection
        self._agent_executor = AgentExecutor(db_connection)
        self._workflow_executor = WorkflowExecutor(db_connection)
    
    async def execute_trigger_result(
        self,
        agent_id: str,
        trigger_result: TriggerResult,
        trigger_event: TriggerEvent
    ) -> Dict[str, Any]:
        try:
            logger.info(f"Executing trigger for agent {agent_id}: workflow={trigger_result.should_execute_workflow}, agent={trigger_result.should_execute_agent}")
            
            if trigger_result.should_execute_workflow:
                return await self._workflow_executor.execute_triggered_workflow(
                    agent_id=agent_id,
                    workflow_id=trigger_result.workflow_id,
                    workflow_input=trigger_result.workflow_input or {},
                    trigger_result=trigger_result,
                    trigger_event=trigger_event
                )
            else:
                return await self._agent_executor.execute_triggered_agent(
                    agent_id=agent_id,
                    trigger_result=trigger_result,
                    trigger_event=trigger_event
                )
                
        except Exception as e:
            logger.error(f"Failed to execute trigger result: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to execute trigger"
            }


class SessionManager:
    def __init__(self, db_connection: DBConnection):
        self._db = db_connection
    
    async def create_agent_session(
        self,
        agent_id: str,
        agent_config: Dict[str, Any],
        trigger_event: TriggerEvent
    ) -> Tuple[str, str]:
        client = await self._db.client
        
        project_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        account_id = agent_config.get('account_id')
        
        placeholder_name = f"Trigger: {agent_config.get('name', 'Agent')} - {trigger_event.trigger_id[:8]}"
        await client.table('projects').insert({
            "project_id": project_id,
            "account_id": account_id,
            "name": placeholder_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        await self._create_sandbox_for_project(project_id)
        
        await client.table('threads').insert({
            "thread_id": thread_id,
            "project_id": project_id,
            "account_id": account_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        logger.info(f"Created agent session: project={project_id}, thread={thread_id}")
        return thread_id, project_id
    
    async def create_workflow_session(
        self,
        account_id: str,
        workflow_id: str,
        workflow_name: str
    ) -> Tuple[str, str]:
        client = await self._db.client
        
        project_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        await client.table('projects').insert({
            "project_id": project_id,
            "account_id": account_id,
            "name": f"Workflow: {workflow_name}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        await self._create_sandbox_for_project(project_id)
        
        await client.table('threads').insert({
            "thread_id": thread_id,
            "project_id": project_id,
            "account_id": account_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "workflow_execution": True,
                "workflow_id": workflow_id,
                "workflow_name": workflow_name
            }
        }).execute()
        
        logger.info(f"Created workflow session: project={project_id}, thread={thread_id}")
        return thread_id, project_id
    
    async def _create_sandbox_for_project(self, project_id: str) -> None:
        client = await self._db.client
        
        try:
            from sandbox.sandbox import create_sandbox, delete_sandbox
            
            sandbox_pass = str(uuid.uuid4())
            sandbox = await create_sandbox(sandbox_pass, project_id)
            sandbox_id = sandbox.id
            
            vnc_link = await sandbox.get_preview_link(6080)
            website_link = await sandbox.get_preview_link(8080)
            vnc_url = self._extract_url(vnc_link)
            website_url = self._extract_url(website_link)
            token = self._extract_token(vnc_link)
            
            update_result = await client.table('projects').update({
                'sandbox': {
                    'id': sandbox_id,
                    'pass': sandbox_pass,
                    'vnc_preview': vnc_url,
                    'sandbox_url': website_url,
                    'token': token
                }
            }).eq('project_id', project_id).execute()
            
            if not update_result.data:
                await delete_sandbox(sandbox_id)
                raise Exception("Database update failed")
                
        except Exception as e:
            await client.table('projects').delete().eq('project_id', project_id).execute()
            raise Exception(f"Failed to create sandbox: {str(e)}")
    
    def _extract_url(self, link) -> str:
        if hasattr(link, 'url'):
            return link.url
        return str(link).split("url='")[1].split("'")[0]
    
    def _extract_token(self, link) -> str:
        if hasattr(link, 'token'):
            return link.token
        if "token='" in str(link):
            return str(link).split("token='")[1].split("'")[0]
        return None
    
    async def start_sandbox(self, project_id: str) -> None:
        try:
            client = await self._db.client
            project_result = await client.table('projects').select('*').eq('project_id', project_id).execute()
            
            if not project_result.data:
                raise Exception("Project not found")
            
            sandbox_info = project_result.data[0].get('sandbox', {})
            sandbox_id = sandbox_info.get('id')
            
            if not sandbox_id:
                raise Exception("No sandbox found for this project")
            
            from sandbox.sandbox import get_or_start_sandbox
            await get_or_start_sandbox(sandbox_id)
            logger.info(f"Started sandbox {sandbox_id} for project {project_id}")
            
        except Exception as e:
            logger.error(f"Failed to start sandbox for project {project_id}: {e}")
            raise Exception(f"Failed to initialize sandbox: {e}")


class AgentExecutor:
    def __init__(self, db_connection: DBConnection):
        self._db = db_connection
        self._session_manager = SessionManager(db_connection)
    
    async def execute_triggered_agent(
        self,
        agent_id: str,
        trigger_result: TriggerResult,
        trigger_event: TriggerEvent
    ) -> Dict[str, Any]:
        try:
            agent_config = await self._get_agent_config(agent_id)
            if not agent_config:
                raise ValueError(f"Agent {agent_id} not found")
            
            thread_id, project_id = await self._session_manager.create_agent_session(
                agent_id, agent_config, trigger_event
            )
            
            await self._create_initial_message(
                thread_id, trigger_result.agent_prompt, trigger_result.execution_variables.variables
            )
            
            agent_run_id = await self._start_agent_execution(
                thread_id, project_id, agent_config, trigger_result.execution_variables.variables
            )
            
            return {
                "success": True,
                "thread_id": thread_id,
                "agent_run_id": agent_run_id,
                "message": "Agent execution started successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to execute triggered agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start agent execution"
            }
    
    async def _get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        from agent.versioning.domain.entities import AgentId
        from agent.versioning.infrastructure.dependencies import set_db_connection, get_container
        
        set_db_connection(self._db)
        
        try:
            client = await self._db.client
            agent_result = await client.table('agents').select('account_id, name').eq('agent_id', agent_id).execute()
            if not agent_result.data:
                return None
            
            agent_data = agent_result.data[0]
            
            container = get_container()
            version_service = await container.get_version_service()
            agent_id_obj = AgentId.from_string(agent_id)
            
            active_version = await version_service.version_repo.find_active_version(agent_id_obj)
            if not active_version:
                return {
                    'agent_id': agent_id,
                    'account_id': agent_data.get('account_id'),
                    'name': agent_data.get('name', 'Unknown Agent'),
                    'system_prompt': 'You are a helpful AI assistant.',
                    'configured_mcps': [],
                    'custom_mcps': [],
                    'agentpress_tools': {},
                }
            
            return {
                'agent_id': agent_id,
                'account_id': agent_data.get('account_id'),
                'name': agent_data.get('name', 'Unknown Agent'),
                'system_prompt': active_version.system_prompt.value,
                'configured_mcps': [
                    {
                        'name': mcp.name,
                        'type': mcp.type,
                        'config': mcp.config,
                        'enabledTools': mcp.enabled_tools
                    }
                    for mcp in active_version.configured_mcps
                ],
                'custom_mcps': [
                    {
                        'name': mcp.name,
                        'type': mcp.type,
                        'config': mcp.config,
                        'enabledTools': mcp.enabled_tools
                    }
                    for mcp in active_version.custom_mcps
                ],
                'agentpress_tools': active_version.tool_configuration.tools,
                'current_version_id': str(active_version.version_id),
                'version_name': active_version.version_name
            }
            
        except Exception as e:
            logger.warning(f"Failed to get agent config using versioning system: {e}")
            return None
    
    async def _create_initial_message(
        self, 
        thread_id: str, 
        prompt: str, 
        trigger_data: Dict[str, Any]
    ) -> None:
        client = await self._db.client
        
        import json
        message_payload = {"role": "user", "content": prompt}
        
        await client.table('messages').insert({
            "message_id": str(uuid.uuid4()),
            "thread_id": thread_id,
            "type": "user",
            "is_llm_message": True,
            "content": json.dumps(message_payload),
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    
    async def _start_agent_execution(
        self,
        thread_id: str,
        project_id: str,
        agent_config: Dict[str, Any],
        trigger_variables: Dict[str, Any]
    ) -> str:
        client = await self._db.client
        model_name = "anthropic/claude-sonnet-4-20250514"
        
        agent_run = await client.table('agent_runs').insert({
            "thread_id": thread_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_config.get('agent_id'),
            "agent_version_id": agent_config.get('current_version_id'),
            "metadata": {
                "model_name": model_name,
                "enable_thinking": False,
                "reasoning_effort": "low",
                "enable_context_manager": True,
                "trigger_execution": True,
                "trigger_variables": trigger_variables
            }
        }).execute()
        
        agent_run_id = agent_run.data[0]['id']
        
        await self._register_agent_run(agent_run_id)
        
        run_agent_background.send(
            agent_run_id=agent_run_id,
            thread_id=thread_id,
            instance_id="trigger_executor",
            project_id=project_id,
            model_name=model_name,
            enable_thinking=False,
            reasoning_effort="low",
            stream=False,
            enable_context_manager=True,
            agent_config=agent_config,
            is_agent_builder=False,
            target_agent_id=None,
            request_id=structlog.contextvars.get_contextvars().get('request_id'),
        )
        
        logger.info(f"Started agent execution: {agent_run_id}")
        return agent_run_id
    
    async def _register_agent_run(self, agent_run_id: str) -> None:
        try:
            instance_key = f"active_run:trigger_executor:{agent_run_id}"
            await redis.set(instance_key, "running", ex=redis.REDIS_KEY_TTL)
        except Exception as e:
            logger.warning(f"Failed to register agent run in Redis: {e}")


class WorkflowExecutor:
    def __init__(self, db_connection: DBConnection):
        self._db = db_connection
        self._session_manager = SessionManager(db_connection)
        self._workflow_prompt_builder = WorkflowPromptBuilder()
    
    async def execute_triggered_workflow(
        self,
        agent_id: str,
        workflow_id: str,
        workflow_input: Dict[str, Any],
        trigger_result: TriggerResult,
        trigger_event: TriggerEvent
    ) -> Dict[str, Any]:
        try:
            workflow_config, steps_json = await self._get_workflow_data(workflow_id, agent_id)
            agent_config, account_id = await self._get_agent_data(agent_id)
            
            enhanced_agent_config = await self._enhance_agent_config_for_workflow(
                agent_config, workflow_config, steps_json, workflow_input
            )
            
            thread_id, project_id = await self._session_manager.create_workflow_session(
                account_id, workflow_id, workflow_config['name']
            )
            
            await self._validate_workflow_execution(account_id)
            
            await self._session_manager.start_sandbox(project_id)
            execution_id = await self._create_workflow_execution_record(
                workflow_id, agent_id, thread_id, workflow_input, trigger_result
            )
            
            await self._create_workflow_message(thread_id, workflow_config, workflow_input)
            agent_run_id = await self._start_workflow_agent_execution(
                thread_id, project_id, enhanced_agent_config
            )
            
            return {
                "success": True,
                "execution_id": execution_id,
                "thread_id": thread_id,
                "agent_run_id": agent_run_id,
                "message": "Workflow execution started successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to execute triggered workflow {workflow_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start workflow execution"
            }
    
    async def _get_workflow_data(self, workflow_id: str, agent_id: str) -> Tuple[Dict[str, Any], list]:
        client = await self._db.client
        
        workflow_result = await client.table('agent_workflows').select('*').eq('id', workflow_id).eq('agent_id', agent_id).execute()
        if not workflow_result.data:
            raise ValueError(f"Workflow {workflow_id} not found for agent {agent_id}")
        
        workflow_config = workflow_result.data[0]
        if workflow_config['status'] != 'active':
            raise ValueError(f"Workflow {workflow_id} is not active")
        
        if workflow_config.get('steps'):
            steps_json = workflow_config['steps']
        else:
            steps_json = await self._get_legacy_workflow_steps(workflow_id)
        
        return workflow_config, steps_json
    
    async def _get_legacy_workflow_steps(self, workflow_id: str) -> list:
        client = await self._db.client
        workflow_steps_result = await client.table('workflow_steps').select('*').eq('workflow_id', workflow_id).order('step_order').execute()
        
        return [{
            'name': step_data['name'],
            'description': step_data.get('description'),
            'type': step_data['type'],
            'config': step_data.get('config', {}),
            'conditions': step_data.get('conditions'),
            'order': step_data['step_order']
        } for step_data in workflow_steps_result.data]
    
    async def _get_agent_data(self, agent_id: str) -> Tuple[Dict[str, Any], str]:
        from agent.versioning.domain.entities import AgentId
        from agent.versioning.infrastructure.dependencies import set_db_connection
        
        set_db_connection(self._db)
        
        try:
            client = await self._db.client
            agent_result = await client.table('agents').select('account_id, name').eq('agent_id', agent_id).execute()
            if not agent_result.data:
                raise ValueError(f"Agent {agent_id} not found")
            
            agent_data = agent_result.data[0]
            account_id = agent_data['account_id']
            
            from agent.versioning.infrastructure.dependencies import get_container
            container = get_container()
            version_service = await container.get_version_service()
            agent_id_obj = AgentId.from_string(agent_id)
            
            active_version = await version_service.version_repo.find_active_version(agent_id_obj)
            if not active_version:
                raise ValueError(f"No active version found for agent {agent_id}")
            
            agent_config = {
                'agent_id': agent_id,
                'name': agent_data.get('name', 'Unknown Agent'),
                'system_prompt': active_version.system_prompt.value,
                'configured_mcps': [
                    {
                        'name': mcp.name,
                        'type': mcp.type,
                        'config': mcp.config,
                        'enabledTools': mcp.enabled_tools
                    }
                    for mcp in active_version.configured_mcps
                ],
                'custom_mcps': [
                    {
                        'name': mcp.name,
                        'type': mcp.type,
                        'config': mcp.config,
                        'enabledTools': mcp.enabled_tools
                    }
                    for mcp in active_version.custom_mcps
                ],
                'agentpress_tools': active_version.tool_configuration.tools,
                'current_version_id': str(active_version.version_id),
                'version_name': active_version.version_name
            }
            
            return agent_config, account_id
            
        except Exception as e:
            raise ValueError(f"Failed to get agent configuration using versioning system: {str(e)}")
    
    async def _enhance_agent_config_for_workflow(
        self,
        agent_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        steps_json: list,
        workflow_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        available_tools = self._workflow_prompt_builder.get_available_tools(agent_config)
        workflow_prompt = self._workflow_prompt_builder.build_workflow_system_prompt(
            workflow_config, steps_json, workflow_input, available_tools
        )
        
        enhanced_config = agent_config.copy()
        enhanced_config['system_prompt'] = f"""{agent_config['system_prompt']}

--- WORKFLOW EXECUTION MODE ---
{workflow_prompt}"""
        
        return enhanced_config
    
    async def _validate_workflow_execution(self, account_id: str) -> None:
        from utils.config import config
        from services.billing import check_billing_status, can_use_model
        
        client = await self._db.client
        model_name = config.MODEL_TO_USE or "anthropic/claude-sonnet-4-20250514"
        
        can_use, model_message, _ = await can_use_model(client, account_id, model_name)
        if not can_use:
            raise Exception(f"Model access denied: {model_message}")
            
        can_run, billing_message, _ = await check_billing_status(client, account_id)
        if not can_run:
            raise Exception(f"Billing check failed: {billing_message}")
    
    async def _create_workflow_execution_record(
        self,
        workflow_id: str,
        agent_id: str,
        thread_id: str,
        workflow_input: Dict[str, Any],
        trigger_result: TriggerResult
    ) -> str:
        client = await self._db.client
        
        execution_result = await client.table('workflow_executions').insert({
            'workflow_id': workflow_id,
            'agent_id': agent_id,
            'thread_id': thread_id,
            'triggered_by': trigger_result.execution_variables.variables.get('triggered_by', 'trigger'),
            'status': 'running',
            'input_data': workflow_input
        }).execute()
        
        return execution_result.data[0]['id']
    
    async def _create_workflow_message(
        self,
        thread_id: str,
        workflow_config: Dict[str, Any],
        workflow_input: Dict[str, Any]
    ) -> None:
        client = await self._db.client
        
        import json
        message_content = f"Execute workflow: {workflow_config['name']}\n\nInput: {json.dumps(workflow_input) if workflow_input else 'None'}"
        
        await client.table('messages').insert({
            "message_id": str(uuid.uuid4()),
            "thread_id": thread_id,
            "type": "user",
            "is_llm_message": True,
            "content": json.dumps({"role": "user", "content": message_content}),
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    
    async def _start_workflow_agent_execution(
        self,
        thread_id: str,
        project_id: str,
        agent_config: Dict[str, Any]
    ) -> str:
        from utils.config import config
        
        client = await self._db.client
        model_name = config.MODEL_TO_USE or "anthropic/claude-sonnet-4-20250514"
        
        agent_run = await client.table('agent_runs').insert({
            "thread_id": thread_id,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_config.get('agent_id'),
            "agent_version_id": agent_config.get('current_version_id')
        }).execute()
        
        agent_run_id = agent_run.data[0]['id']
        
        await self._register_workflow_run(agent_run_id)
        
        run_agent_background.send(
            agent_run_id=agent_run_id,
            thread_id=thread_id,
            instance_id=getattr(config, 'INSTANCE_ID', 'default'),
            project_id=project_id,
            model_name=model_name,
            enable_thinking=False,
            reasoning_effort='medium',
            stream=False,
            enable_context_manager=True,
            agent_config=agent_config,
            is_agent_builder=False,
            target_agent_id=None,
            request_id=None,
        )
        
        logger.info(f"Started workflow agent execution: {agent_run_id}")
        return agent_run_id
    
    async def _register_workflow_run(self, agent_run_id: str) -> None:
        try:
            from utils.config import config
            instance_id = getattr(config, 'INSTANCE_ID', 'default')
            instance_key = f"active_run:{instance_id}:{agent_run_id}"
            await redis.set(instance_key, "running", ex=redis.REDIS_KEY_TTL)
        except Exception as e:
            logger.warning(f"Failed to register workflow run in Redis: {e}")


class WorkflowPromptBuilder:
    def get_available_tools(self, agent_config: Dict[str, Any]) -> list:
        available_tools = []
        agentpress_tools = agent_config.get('agentpress_tools', {})
        tool_mapping = {
            'sb_shell_tool': ['execute_command'],
            'sb_files_tool': ['create_file', 'str_replace', 'full_file_rewrite', 'delete_file'],
            'sb_browser_tool': ['browser_navigate_to', 'browser_take_screenshot'],
            'sb_vision_tool': ['see_image'],
            'sb_deploy_tool': ['deploy'],
            'sb_expose_tool': ['expose_port'],
            'web_search_tool': ['web_search'],
            'data_providers_tool': ['get_data_provider_endpoints', 'execute_data_provider_call']
        }
        
        for tool_key, tool_names in tool_mapping.items():
            if agentpress_tools.get(tool_key, {}).get('enabled', False):
                available_tools.extend(tool_names)
        
        all_mcps = []
        if agent_config.get('configured_mcps'):
            all_mcps.extend(agent_config['configured_mcps'])
        if agent_config.get('custom_mcps'):
            all_mcps.extend(agent_config['custom_mcps'])
        
        for mcp in all_mcps:
            enabled_tools_list = mcp.get('enabledTools', [])
            available_tools.extend(enabled_tools_list)
        
        return available_tools
    
    def build_workflow_system_prompt(
        self,
        workflow: dict,
        steps_json: list,
        input_data: dict = None,
        available_tools: list = None
    ) -> str:
        return format_workflow_for_llm(
            workflow_config=workflow,
            steps=steps_json,
            input_data=input_data,
            available_tools=available_tools
        )
    
 