from typing import Dict, List, Any, Optional
import json


class WorkflowParser:
    def __init__(self):
        self.step_counter = 0
        self.parsed_steps = []
    
    def parse_workflow_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.step_counter = 0
        self.parsed_steps = []
        
        filtered_steps = [step for step in steps if step.get('name') != 'Start' or step.get('description') != 'Click to add steps or use the Add Node button']
        
        return self._parse_steps_recursive(filtered_steps)
    
    def _parse_steps_recursive(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        
        for step in steps:
            parsed_step = self._parse_single_step(step)
            if parsed_step:
                result.append(parsed_step)
        
        return result
    
    def _parse_single_step(self, step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        step_type = step.get('type')
        step_name = step.get('name', '')
        
        if step_type == 'instruction':
            return self._parse_instruction_step(step)
        elif step_type == 'condition':
            return self._parse_condition_step(step)
        else:
            return self._parse_instruction_step(step)
    
    def _parse_instruction_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        self.step_counter += 1
        
        parsed_step = {
            "step": step.get('name', f'Step {self.step_counter}'),
            "step_number": self.step_counter
        }
        
        description = step.get('description', '').strip()
        if description:
            parsed_step["description"] = description
        
        tool_name = step.get('config', {}).get('tool_name')
        if tool_name:
            if ':' in tool_name:
                _, clean_tool_name = tool_name.split(':', 1)
                parsed_step["tool"] = clean_tool_name
            else:
                parsed_step["tool"] = tool_name
        
        children = step.get('children', [])
        if children:
            condition_children = [child for child in children if child.get('type') == 'condition']
            instruction_children = [child for child in children if child.get('type') == 'instruction']
            
            if condition_children:
                parsed_step["conditions"] = self._parse_condition_branches(condition_children)
            
            if instruction_children:
                parsed_step["then"] = self._parse_steps_recursive(instruction_children)
        
        return parsed_step
    
    def _parse_condition_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        conditions = step.get('conditions', {})
        condition_type = conditions.get('type', 'if')
        expression = conditions.get('expression', '').strip()
        
        parsed_condition = {}
        
        if condition_type == 'if':
            parsed_condition["condition"] = expression if expression else "true"
        elif condition_type == 'elseif':
            parsed_condition["condition"] = f"else if {expression}" if expression else "else if true"
        elif condition_type == 'else':
            parsed_condition["condition"] = "else"
        
        children = step.get('children', [])
        if children:
            parsed_condition["then"] = self._parse_steps_recursive(children)
        
        return parsed_condition
    
    def _parse_condition_branches(self, condition_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        branches = []
        
        for condition_step in condition_steps:
            branch = self._parse_condition_step(condition_step)
            if branch:
                branches.append(branch)
        
        return branches
    
    def get_workflow_summary(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        def count_steps_recursive(steps_list):
            count = 0
            conditions_count = 0
            max_depth = 0
            
            for step in steps_list:
                if "step_number" in step:
                    count += 1
                
                if "conditions" in step:
                    conditions_count += len(step["conditions"])
                    for condition in step["conditions"]:
                        if "then" in condition:
                            sub_count, sub_conditions, sub_depth = count_steps_recursive(condition["then"])
                            count += sub_count
                            conditions_count += sub_conditions
                            max_depth = max(max_depth, sub_depth + 1)
                
                if "then" in step:
                    sub_count, sub_conditions, sub_depth = count_steps_recursive(step["then"])
                    count += sub_count
                    conditions_count += sub_conditions
                    max_depth = max(max_depth, sub_depth + 1)
            
            return count, conditions_count, max_depth
        
        total_steps, total_conditions, max_nesting_depth = count_steps_recursive(steps)
        
        return {
            "total_steps": total_steps,
            "total_conditions": total_conditions,
            "max_nesting_depth": max_nesting_depth,
            "has_conditional_logic": total_conditions > 0
        }


def format_workflow_for_llm(
    workflow_config: Dict[str, Any],
    steps: List[Dict[str, Any]],
    input_data: Dict[str, Any] = None,
    available_tools: List[str] = None
) -> str:
    parser = WorkflowParser()
    parsed_steps = parser.parse_workflow_steps(steps)
    summary = parser.get_workflow_summary(parsed_steps)
    
    llm_workflow = {
        "workflow": workflow_config.get('name', 'Untitled Workflow'),
        "steps": parsed_steps
    }

    if workflow_config.get('description'):
        llm_workflow["description"] = workflow_config['description']
    
    llm_workflow["summary"] = summary
    
    workflow_json = json.dumps(llm_workflow, indent=2)
    tools_list = ', '.join(available_tools) if available_tools else 'Use any available tools from your system prompt'
    input_json = json.dumps(input_data, indent=2) if input_data else 'None provided'
    
    return f"""You are executing a structured workflow. Follow the steps exactly as specified in the JSON below.

WORKFLOW STRUCTURE:
{workflow_json}

EXECUTION INSTRUCTIONS:
1. Execute each step in the order presented
2. For steps with a "tool" field, you MUST use that specific tool
3. For steps with "conditions" field:
   - Evaluate each condition in order
   - Execute the "then" steps for the first condition that evaluates to true
   - For "else" conditions, execute if no previous conditions were true
4. Provide clear progress updates as you complete each step
5. If a tool is not available, explain what you would do instead

WORKFLOW STATISTICS:
- Total Steps: {summary['total_steps']}
- Conditional Branches: {summary['total_conditions']}
- Maximum Nesting Depth: {summary['max_nesting_depth']}
- Has Conditional Logic: {summary['has_conditional_logic']}

AVAILABLE TOOLS:
{tools_list}

IMPORTANT TOOL USAGE:
- When a step specifies a tool, that tool MUST be used
- If the specified tool is not available, explain what you would do instead
- Use only the tools that are listed as available

WORKFLOW INPUT DATA:
{input_json}

Begin executing the workflow now, starting with the first step."""
