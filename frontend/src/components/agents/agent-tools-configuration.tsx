import React, { useState } from 'react';
import { Search, Settings2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DEFAULT_AGENTPRESS_TOOLS, getToolDisplayName } from './tools';

interface AgentToolsConfigurationProps {
  tools: Record<string, { enabled: boolean; description: string }>;
  onToolsChange: (tools: Record<string, { enabled: boolean; description: string }>) => void;
}

export const AgentToolsConfiguration = ({ tools, onToolsChange }: AgentToolsConfigurationProps) => {
  const [searchQuery, setSearchQuery] = useState<string>('');

  const handleToolToggle = (toolName: string, enabled: boolean) => {
    const updatedTools = {
      ...tools,
      [toolName]: {
        ...tools[toolName],
        enabled
      }
    };
    onToolsChange(updatedTools);
  };

  const getSelectedToolsCount = (): number => {
    return Object.values(tools).filter(tool => tool.enabled).length;
  };

  const getFilteredTools = (): Array<[string, any]> => {
    let toolEntries = Object.entries(DEFAULT_AGENTPRESS_TOOLS);
    
    if (searchQuery) {
      toolEntries = toolEntries.filter(([toolName, toolInfo]) => 
        getToolDisplayName(toolName).toLowerCase().includes(searchQuery.toLowerCase()) ||
        toolInfo.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    
    return toolEntries;
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex-shrink-0 mb-4">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm text-muted-foreground">
            {getSelectedToolsCount()} selected
          </span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="gap-4 grid grid-cols-1 md:grid-cols-2">
          {getFilteredTools().map(([toolName, toolInfo]) => (
            <div 
              key={toolName} 
              className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg border hover:border-border/80 transition-colors"
            >
              <div className={`w-10 h-10 rounded-lg ${toolInfo.color} flex items-center justify-center flex-shrink-0`}>
                <span className="text-lg">{toolInfo.icon}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="font-medium text-sm">
                    {getToolDisplayName(toolName)}
                  </h4>
                  <Switch
                    checked={tools[toolName]?.enabled || false}
                    onCheckedChange={(checked) => handleToolToggle(toolName, checked)}
                    className="flex-shrink-0"
                  />
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {toolInfo.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {getFilteredTools().length === 0 && (
          <div className="text-center py-8">
            <div className="text-4xl mb-3">🔍</div>
            <h3 className="text-sm font-medium mb-1">No tools found</h3>
            <p className="text-xs text-muted-foreground">Try adjusting your search criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}; 