'use client';

import React, { useState, useMemo } from 'react';
import { Plus, Filter, Globe, ChevronDown, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { SearchBar } from './search-bar';
import { EmptyState } from '../empty-state';
import { AgentsGrid } from '../agents-grid';
import { LoadingState } from '../loading-state';
import { Pagination } from '../pagination';
import { Badge } from '@/components/ui/badge';
import { AgentCard } from './agent-card';

type AgentFilter = 'all' | 'templates';

interface MyAgentsTabProps {
  agentsSearchQuery: string;
  setAgentsSearchQuery: (value: string) => void;
  agentsLoading: boolean;
  agents: any[];
  agentsPagination: any;
  viewMode: 'grid' | 'list';
  onCreateAgent: () => void;
  onEditAgent: (agentId: string) => void;
  onDeleteAgent: (agentId: string) => void;
  onToggleDefault: (agentId: string, currentDefault: boolean) => void;
  onClearFilters: () => void;
  deleteAgentMutation: any;
  setAgentsPage: (page: number) => void;

  myTemplates: any[];
  templatesLoading: boolean;
  templatesError: any;
  templatesActioningId: string | null;
  onPublish: (template: any) => void;
  onUnpublish: (templateId: string, templateName: string) => void;
  getTemplateStyling: (template: any) => { avatar: string; color: string };

  onPublishAgent?: (agent: any) => void;
  publishingAgentId?: string | null;
}

const filterOptions = [
  { value: 'all', label: 'All Agents', icon: Users },
  { value: 'templates', label: 'Templates', icon: Globe },
];

export const MyAgentsTab = ({
  agentsSearchQuery,
  setAgentsSearchQuery,
  agentsLoading,
  agents,
  agentsPagination,
  viewMode,
  onCreateAgent,
  onEditAgent,
  onDeleteAgent,
  onToggleDefault,
  onClearFilters,
  deleteAgentMutation,
  setAgentsPage,
  myTemplates,
  templatesLoading,
  templatesError,
  templatesActioningId,
  onPublish,
  onUnpublish,
  getTemplateStyling,
  onPublishAgent,
  publishingAgentId
}: MyAgentsTabProps) => {
  const [agentFilter, setAgentFilter] = useState<AgentFilter>('all');

  const filteredAgents = useMemo(() => {
    if (agentFilter === 'templates') {
      return [];
    }
    return agents;
  }, [agents, agentFilter]);

  const templateAgentsCount = useMemo(() => {
    return myTemplates?.length || 0;
  }, [myTemplates]);

  const handleClearFilters = () => {
    setAgentFilter('all');
    onClearFilters();
  };

  const currentFilter = filterOptions.find(filter => filter.value === agentFilter);
  const CurrentFilterIcon = currentFilter?.icon || Users;

  const getCountForFilter = (filterValue: string) => {
    if (filterValue === 'templates') {
      return templateAgentsCount;
    }
    return agents.length;
  };

  const renderTemplates = () => {
    if (templatesLoading) {
      return <LoadingState viewMode={viewMode} />;
    }

    if (templatesError) {
      return (
        <div className="text-center py-16">
          <p className="text-destructive">Failed to load templates</p>
        </div>
      );
    }

    if (!myTemplates || myTemplates.length === 0) {
      return (
        <div className="text-center py-16">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-primary/20 to-primary/10 rounded-3xl flex items-center justify-center mb-6">
            <Globe className="h-10 w-10 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-3">No published templates yet</h3>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Publish your agents to the marketplace to share them with the community and track their usage.
          </p>
        </div>
      );
    }

    return (
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {myTemplates.map((template) => {
          const isActioning = templatesActioningId === template.template_id;
          return (
            <AgentCard
              key={template.template_id}
              mode="template"
              data={template}
              styling={getTemplateStyling(template)}
              isActioning={isActioning}
              onPrimaryAction={
                template.is_public 
                  ? () => onUnpublish(template.template_id, template.name)
                  : () => onPublish(template)
              }
              onSecondaryAction={template.is_public ? () => {/* View in marketplace */} : undefined}
            />
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6 mt-8 flex flex-col min-h-full">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between mb-6">
        <SearchBar
          placeholder="Search your agents..."
          value={agentsSearchQuery}
          onChange={setAgentsSearchQuery}
        />
        
        <div className="flex items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="rounded-xl">
                <CurrentFilterIcon className="h-4 w-4 mr-2" />
                {currentFilter?.label}
                <Badge variant="outline">
                  {getCountForFilter(agentFilter)}
                </Badge>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {filterOptions.map((filter) => {
                const Icon = filter.icon;
                const count = getCountForFilter(filter.value);
                return (
                  <DropdownMenuItem
                    key={filter.value}
                    onClick={() => setAgentFilter(filter.value as AgentFilter)}
                    className="cursor-pointer"
                  >
                    <Icon className="h-4 w-4" />
                    {filter.label}
                    <Badge variant="outline" className="ml-auto">
                      {count}
                    </Badge>
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
          
          <Button onClick={onCreateAgent} className='rounded-xl'>
            <Plus className="h-4 w-4" />
            Create Agent
          </Button>
        </div>
      </div>

      <div className="flex-1">
        {agentFilter === 'templates' ? (
          renderTemplates()
        ) : (
          <>
            {agentsLoading ? (
              <LoadingState viewMode={viewMode} />
            ) : filteredAgents.length === 0 ? (
              <EmptyState
                hasAgents={(agentsPagination?.total || 0) > 0}
                onCreateAgent={onCreateAgent}
                onClearFilters={handleClearFilters}
              />
            ) : (
              <AgentsGrid
                agents={filteredAgents}
                onEditAgent={onEditAgent}
                onDeleteAgent={onDeleteAgent}
                onToggleDefault={onToggleDefault}
                deleteAgentMutation={deleteAgentMutation}
                onPublish={onPublishAgent}
                publishingId={publishingAgentId}
              />
            )}

            {agentsPagination && agentsPagination.pages > 1 && (
              <Pagination
                currentPage={agentsPagination.page}
                totalPages={agentsPagination.pages}
                onPageChange={setAgentsPage}
                isLoading={agentsLoading}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}; 