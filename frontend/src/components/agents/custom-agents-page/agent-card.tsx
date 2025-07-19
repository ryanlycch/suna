'use client';

import React from 'react';
import { Download, User, Calendar, CheckCircle, Loader2, Globe, GlobeLock, Eye, Shield, GitBranch } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { MarketplaceTemplate } from '@/components/agents/installation/types';

export type AgentCardMode = 'marketplace' | 'template' | 'agent';

interface BaseAgentData {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  created_at: string;
  avatar?: string;
  avatar_color?: string;
}

interface MarketplaceData extends BaseAgentData {
  is_kortix_team?: boolean;
  download_count: number;
  creator_name?: string;
  marketplace_published_at?: string;
}

interface TemplateData extends BaseAgentData {
  template_id: string;
  is_public?: boolean;
  download_count?: number;
}

interface AgentData extends BaseAgentData {
  agent_id: string;
  is_default?: boolean;
  is_public?: boolean;
  marketplace_published_at?: string;
  download_count?: number;
  current_version?: {
    version_id: string;
    version_name: string;
    version_number: number;
  };
}

type AgentCardData = MarketplaceData | TemplateData | AgentData;

interface AgentCardProps {
  mode: AgentCardMode;
  data: AgentCardData;
  styling: {
    avatar: string;
    color: string;
  };
  isActioning?: boolean;
  onPrimaryAction?: (data: any, e?: React.MouseEvent) => void;
  onSecondaryAction?: (data: any, e?: React.MouseEvent) => void;
  onClick?: (data: any) => void;
}

// Badge components for each mode
const MarketplaceBadge: React.FC<{ isKortixTeam?: boolean }> = ({ isKortixTeam }) => {
  if (isKortixTeam) {
    return (
      <Badge variant="secondary" className="bg-blue-100 text-blue-700 border-0 dark:bg-blue-950 dark:text-blue-300">
        <CheckCircle className="h-3 w-3" />
        Kortix
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="bg-green-100 text-green-700 border-0 dark:bg-green-950 dark:text-green-300">
      <User className="h-3 w-3" />
      Community
    </Badge>
  );
};

const TemplateBadge: React.FC<{ isPublic?: boolean }> = ({ isPublic }) => {
  if (isPublic) {
    return (
      <Badge variant="default" className="bg-green-100 text-green-700 border-0 dark:bg-green-950 dark:text-green-300">
        <Globe className="h-3 w-3" />
        Public
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="bg-gray-100 text-gray-700 border-0 dark:bg-gray-800 dark:text-gray-300">
      <GlobeLock className="h-3 w-3" />
      Private
    </Badge>
  );
};

const AgentBadges: React.FC<{ agent: AgentData }> = ({ agent }) => (
  <div className="flex gap-1">
    {agent.current_version && (
      <Badge variant="outline" className="text-xs">
        <GitBranch className="h-3 w-3 mr-1" />
        {agent.current_version.version_name}
      </Badge>
    )}
    {agent.is_public && (
      <Badge variant="default" className="bg-green-100 text-green-700 border-0 dark:bg-green-950 dark:text-green-300 text-xs">
        <Globe className="h-3 w-3 mr-1" />
        Published
      </Badge>
    )}
  </div>
);

// Metadata components for each mode
const MarketplaceMetadata: React.FC<{ data: MarketplaceData }> = ({ data }) => (
  <div className="flex items-center justify-between text-xs text-muted-foreground">
    <div className="flex items-center gap-1">
      {data.is_kortix_team ? (
        <>
          <Download className="h-3 w-3" />
          <span>{data.download_count} installs</span>
        </>
      ) : (
        <>
          <User className="h-3 w-3" />
          <span>by {data.creator_name}</span>
        </>
      )}
    </div>
    <div className="flex items-center gap-1">
      <Calendar className="h-3 w-3" />
      <span>{new Date(data.marketplace_published_at || data.created_at).toLocaleDateString()}</span>
    </div>
  </div>
);

const TemplateMetadata: React.FC<{ data: TemplateData }> = ({ data }) => (
  <div className="space-y-1 text-xs text-muted-foreground">
    <div className="flex items-center gap-1">
      <Calendar className="h-3 w-3" />
      <span>Created {new Date(data.created_at).toLocaleDateString()}</span>
    </div>
  </div>
);

const AgentMetadata: React.FC<{ data: AgentData }> = ({ data }) => (
  <div className="space-y-1 text-xs text-muted-foreground">
    <div className="flex items-center justify-between">
      <span>By me</span>
      <div className="flex items-center gap-1">
        <Calendar className="h-3 w-3" />
        <span>{new Date(data.created_at).toLocaleDateString()}</span>
      </div>
    </div>
    {data.is_public && data.marketplace_published_at && (
      <div className="flex items-center gap-1">
        <Download className="h-3 w-3" />
        <span>{data.download_count || 0} downloads</span>
      </div>
    )}
  </div>
);

// Action components for each mode
const MarketplaceActions: React.FC<{ 
  onAction?: (data: any, e?: React.MouseEvent) => void;
  isActioning?: boolean;
  data: any;
}> = ({ onAction, isActioning, data }) => (
  <Button 
    onClick={(e) => onAction?.(data, e)}
    disabled={isActioning}
    className="w-full"
    size="sm"
  >
    {isActioning ? (
      <>
        <Loader2 className="h-4 w-4 animate-spin " />
        Installing...
      </>
    ) : (
      <>
        <Download className="h-4 w-4 " />
        Install Agent
      </>
    )}
  </Button>
);

const TemplateActions: React.FC<{ 
  data: TemplateData;
  onPrimaryAction?: (data: any, e?: React.MouseEvent) => void;
  onSecondaryAction?: (data: any, e?: React.MouseEvent) => void;
  isActioning?: boolean;
}> = ({ data, onPrimaryAction, onSecondaryAction, isActioning }) => (
  <div className="space-y-2">
    {data.is_public ? (
      <>
        <Button
          onClick={(e) => onPrimaryAction?.(data, e)}
          disabled={isActioning}
          variant="outline"
          className="w-full"
          size="sm"
        >
          {isActioning ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin " />
              Unpublishing...
            </>
          ) : (
            <>
              <GlobeLock className="h-3 w-3 " />
              Make Private
            </>
          )}
        </Button>
      </>
    ) : (
      <Button
        onClick={(e) => onPrimaryAction?.(data, e)}
        disabled={isActioning}
        variant="default"
        className="w-full"
        size="sm"
      >
        {isActioning ? (
          <>
            <Loader2 className="h-3 w-3 animate-spin " />
            Publishing...
          </>
        ) : (
          <>
            <Globe className="h-3 w-3 " />
            Publish to Marketplace
          </>
        )}
      </Button>
    )}
  </div>
);

const CardAvatar: React.FC<{ avatar: string; color: string }> = ({ avatar, color }) => (
  <div 
    className="relative h-14 w-14 flex items-center justify-center rounded-2xl" 
    style={{ backgroundColor: color }}
  >
    <div className="text-2xl">{avatar}</div>
    <div 
      className="absolute inset-0 rounded-2xl pointer-events-none opacity-0 dark:opacity-100 transition-opacity"
      style={{
        boxShadow: `0 16px 48px -8px ${color}70, 0 8px 24px -4px ${color}50`
      }}
    />
  </div>
);

const TagList: React.FC<{ tags?: string[] }> = ({ tags }) => {
  return (
    <div className="flex flex-wrap gap-1 min-h-[1.25rem]">
      {tags && tags.length > 0 && (
        <>
          {tags.slice(0, 2).map(tag => (
            <Badge key={tag} variant="outline" className="text-xs border-border/50">
              {tag}
            </Badge>
          ))}
          {tags.length > 2 && (
            <Badge variant="outline" className="text-xs border-border/50">
              +{tags.length - 2}
            </Badge>
          )}
        </>
      )}
    </div>
  );
};

export const AgentCard: React.FC<AgentCardProps> = ({
  mode,
  data,
  styling,
  isActioning = false,
  onPrimaryAction,
  onSecondaryAction,
  onClick
}) => {
  const { avatar, color } = styling;
  
  const cardClassName = "group relative bg-card rounded-2xl overflow-hidden shadow-sm transition-all duration-300 border border-border/50 hover:border-primary/20 cursor-pointer flex flex-col h-full";
  
  const renderBadge = () => {
    switch (mode) {
      case 'marketplace':
        return <MarketplaceBadge isKortixTeam={(data as MarketplaceData).is_kortix_team} />;
      case 'template':
        return <TemplateBadge isPublic={(data as TemplateData).is_public} />;
      case 'agent':
        return <AgentBadges agent={data as AgentData} />;
      default:
        return null;
    }
  };

  const renderMetadata = () => {
    switch (mode) {
      case 'marketplace':
        return <MarketplaceMetadata data={data as MarketplaceData} />;
      case 'template':
        return <TemplateMetadata data={data as TemplateData} />;
      case 'agent':
        return <AgentMetadata data={data as AgentData} />;
      default:
        return null;
    }
  };

  const renderActions = () => {
    switch (mode) {
      case 'marketplace':
        return <MarketplaceActions onAction={onPrimaryAction} isActioning={isActioning} data={data} />;
      case 'template':
        return <TemplateActions 
          data={data as TemplateData} 
          onPrimaryAction={onPrimaryAction} 
          onSecondaryAction={onSecondaryAction} 
          isActioning={isActioning} 
        />;
      case 'agent':
        return null;
      default:
        return null;
    }
  };

  return (
    <div className={cardClassName} onClick={() => onClick?.(data)}>
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="relative p-6 flex flex-col h-full">
        <div className="flex items-start justify-between mb-4">
          <CardAvatar avatar={avatar} color={color} />
          <div className="flex items-center gap-2">
            {renderBadge()}
            {mode === 'template' && (data as TemplateData).is_public && (data as TemplateData).download_count !== undefined && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Download className="h-3 w-3" />
                <span>{(data as TemplateData).download_count} downloads</span>
              </div>
            )}
          </div>
        </div>
        
        <h3 className="text-lg font-semibold text-foreground mb-2 line-clamp-1">
          {data.name}
        </h3>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-2 min-h-[2.5rem]">
          {data.description || 'No description available'}
        </p>
        
        <div className="flex-1 flex flex-col">
          <div className="min-h-[1.25rem] mb-3">
            <TagList tags={data.tags} />
          </div>
          
          <div className="mt-auto">
            <div className="mb-3">
              {renderMetadata()}
            </div>
            {renderActions()}
          </div>
        </div>
      </div>
    </div>
  );
}; 