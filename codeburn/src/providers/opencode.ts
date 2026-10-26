import { join } from 'path'
import { homedir } from 'os'

import { getShortModelName } from '../models.js'
import { discoverSqliteSessions, createSqliteSessionParser, type SqliteProviderConfig } from './sqlite-session-parser.js'
import type { Provider, SessionSource, SessionParser } from './types.js'

const toolNameMap: Record<string, string> = {
  bash: 'Bash',
  read: 'Read',
  edit: 'Edit',
  write: 'Write',
  glob: 'Glob',
  grep: 'Grep',
  task: 'Agent',
  fetch: 'WebFetch',
  search: 'WebSearch',
  todo: 'TodoWrite',
  skill: 'Skill',
  patch: 'Patch',
}

function getDataDir(dataDir?: string): string {
  const base =
    dataDir ??
    process.env['XDG_DATA_HOME'] ??
    join(homedir(), '.local', 'share')
  return join(base, 'opencode')
}

function getSqliteConfig(dataDir?: string): SqliteProviderConfig {
  return {
    providerName: 'opencode',
    displayName: 'OpenCode',
    dbDir: getDataDir(dataDir),
    dbFilePrefix: 'opencode',
  }
}

export function createOpenCodeProvider(dataDir?: string): Provider {
  const sqliteConfig = getSqliteConfig(dataDir)

  return {
    name: 'opencode',
    displayName: 'OpenCode',

    modelDisplayName(model: string): string {
      const stripped = model.replace(/^[^/]+\//, '')
      return getShortModelName(stripped)
    },

    toolDisplayName(rawTool: string): string {
      return toolNameMap[rawTool] ?? rawTool
    },

    async discoverSessions(): Promise<SessionSource[]> {
      return discoverSqliteSessions(sqliteConfig)
    },

    createSessionParser(source: SessionSource, seenKeys: Set<string>): SessionParser {
      return createSqliteSessionParser(source, seenKeys, sqliteConfig)
    },
  }
}

export const opencode = createOpenCodeProvider()
