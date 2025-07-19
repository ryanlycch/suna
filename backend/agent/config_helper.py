from typing import Dict, Any, Optional, List
from utils.logger import logger


def extract_agent_config(agent_data: Dict[str, Any], version_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    agent_id = agent_data.get('agent_id', 'Unknown')
    
    agent_has_config = bool(agent_data.get('config') and agent_data['config'] != {})
    version_has_config = bool(version_data and version_data.get('config') and version_data['config'] != {})
    
    if version_data and ('configured_mcps' in version_data or 'custom_mcps' in version_data or 'system_prompt' in version_data):
        logger.info(f"Using version data from version manager for agent {agent_id}")
        config = {
            'agent_id': agent_data['agent_id'],
            'name': agent_data['name'],
            'description': agent_data.get('description'),
            'is_default': agent_data.get('is_default', False),
            'account_id': agent_data.get('account_id'),
            'current_version_id': agent_data.get('current_version_id'),
            'version_name': version_data.get('version_name', 'v1'),
            'system_prompt': version_data.get('system_prompt', ''),
            'configured_mcps': version_data.get('configured_mcps', []),
            'custom_mcps': version_data.get('custom_mcps', []),
            'agentpress_tools': version_data.get('agentpress_tools', {}),
            'avatar': agent_data.get('avatar'),
            'avatar_color': agent_data.get('avatar_color'),
            'tools': {
                'agentpress': version_data.get('agentpress_tools', {}),
                'mcp': version_data.get('configured_mcps', []),
                'custom_mcp': version_data.get('custom_mcps', [])
            },
            'metadata': {
                'avatar': agent_data.get('avatar'),
                'avatar_color': agent_data.get('avatar_color')
            }
        }
        return config
    
    if version_data and version_data.get('config') and version_data['config'] != {}:
        config = version_data['config'].copy()
        config['agent_id'] = agent_data['agent_id']
        config['name'] = agent_data['name']
        config['description'] = agent_data.get('description')
        config['is_default'] = agent_data.get('is_default', False)
        config['account_id'] = agent_data.get('account_id')
        config['current_version_id'] = agent_data.get('current_version_id')
        config['version_name'] = version_data.get('version_name', 'v1')
        
        metadata = config.get('metadata', {})
        config['avatar'] = metadata.get('avatar', agent_data.get('avatar'))
        config['avatar_color'] = metadata.get('avatar_color', agent_data.get('avatar_color'))
        
        config['agentpress_tools'] = extract_tools_for_agent_run(config)
        
        config['configured_mcps'] = config.get('tools', {}).get('mcp', [])
        config['custom_mcps'] = config.get('tools', {}).get('custom_mcp', [])
        
        return config
    
    if agent_data.get('config') and agent_data['config'] != {}:
        config = agent_data['config'].copy()
        if 'tools' not in config:
            config['tools'] = {
                'agentpress': {},
                'mcp': [],
                'custom_mcp': []
            }
        if 'metadata' not in config:
            config['metadata'] = {}
            
        config['agent_id'] = agent_data['agent_id']
        config['name'] = agent_data['name']
        config['description'] = agent_data.get('description')
        config['is_default'] = agent_data.get('is_default', False)
        config['account_id'] = agent_data.get('account_id')
        config['current_version_id'] = agent_data.get('current_version_id')
        
        metadata = config.get('metadata', {})
        config['avatar'] = metadata.get('avatar')
        config['avatar_color'] = metadata.get('avatar_color')
        
        config['agentpress_tools'] = extract_tools_for_agent_run(config)
        
        config['configured_mcps'] = config.get('tools', {}).get('mcp', [])
        config['custom_mcps'] = config.get('tools', {}).get('custom_mcp', [])
        
        return config
    
    source_data = version_data if version_data else agent_data
    
    legacy_tools = source_data.get('agentpress_tools', {})
    simplified_tools = {}
    
    for tool_name, tool_config in legacy_tools.items():
        if isinstance(tool_config, dict):
            simplified_tools[tool_name] = tool_config.get('enabled', False)
        elif isinstance(tool_config, bool):
            simplified_tools[tool_name] = tool_config
    
    config = {
        'agent_id': agent_data['agent_id'],
        'name': agent_data['name'],
        'description': agent_data.get('description'),
        'system_prompt': source_data.get('system_prompt', ''),
        'tools': {
            'agentpress': simplified_tools,
            'mcp': source_data.get('configured_mcps', []),
            'custom_mcp': source_data.get('custom_mcps', [])
        },
        'metadata': {
            'avatar': agent_data.get('avatar'),
            'avatar_color': agent_data.get('avatar_color')
        },
        'is_default': agent_data.get('is_default', False),
        'account_id': agent_data.get('account_id'),
        'current_version_id': agent_data.get('current_version_id'),
        'avatar': agent_data.get('avatar'),
        'avatar_color': agent_data.get('avatar_color')
    }
    
    if version_data:
        config['version_name'] = version_data.get('version_name', 'v1')
    
    config['configured_mcps'] = source_data.get('configured_mcps', [])
    config['custom_mcps'] = source_data.get('custom_mcps', [])
    config['agentpress_tools'] = legacy_tools
    
    return config


def build_unified_config(
    system_prompt: str,
    agentpress_tools: Dict[str, Any],
    configured_mcps: List[Dict[str, Any]],
    custom_mcps: Optional[List[Dict[str, Any]]] = None,
    avatar: Optional[str] = None,
    avatar_color: Optional[str] = None
) -> Dict[str, Any]:
    simplified_tools = {}
    for tool_name, tool_config in agentpress_tools.items():
        if isinstance(tool_config, dict):
            simplified_tools[tool_name] = tool_config.get('enabled', False)
        elif isinstance(tool_config, bool):
            simplified_tools[tool_name] = tool_config
    return {
        'system_prompt': system_prompt,
        'tools': {
            'agentpress': simplified_tools,
            'mcp': configured_mcps or [],
            'custom_mcp': custom_mcps or []
        },
        'metadata': {
            'avatar': avatar,
            'avatar_color': avatar_color
        }
    }


def extract_tools_for_agent_run(config: Dict[str, Any]) -> Dict[str, Any]:
    tools = config.get('tools', {})
    agentpress = tools.get('agentpress', {})
    
    legacy_format = {}
    
    for tool_name, enabled in agentpress.items():
        if isinstance(enabled, bool):
            legacy_format[tool_name] = {
                'enabled': enabled,
                'description': ''
            }
        elif isinstance(enabled, dict):
            legacy_format[tool_name] = enabled
    
    return legacy_format


def get_mcp_configs(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    tools = config.get('tools', {})
    all_mcps = []
    
    if 'configured_mcps' in config and config['configured_mcps']:
        for mcp in config['configured_mcps']:
            if mcp not in all_mcps:
                all_mcps.append(mcp)
    
    if 'custom_mcps' in config and config['custom_mcps']:
        for mcp in config['custom_mcps']:
            if mcp not in all_mcps:
                all_mcps.append(mcp)
    
    mcp_list = tools.get('mcp', [])
    if mcp_list:
        for mcp in mcp_list:
            if mcp not in all_mcps:
                all_mcps.append(mcp)
    
    custom_mcp_list = tools.get('custom_mcp', [])
    if custom_mcp_list:
        for mcp in custom_mcp_list:
            if mcp not in all_mcps:
                all_mcps.append(mcp)
    
    return all_mcps 