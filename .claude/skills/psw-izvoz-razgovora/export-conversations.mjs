#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';

const SCRIPT_VERSION = 2;
const WORKSPACE_FOLDERS = ['specs', 'study'];
const INPUT_LIMIT = 2000;
const RESULT_LIMIT = 4000;

function argument(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? null : process.argv[index + 1];
}

function git(args, cwd) {
  try {
    return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return '';
  }
}

function realPath(target) {
  try {
    return fs.realpathSync.native(target);
  } catch {
    return path.resolve(target);
  }
}

function isInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function firstWorkingDirectory(file) {
  const descriptor = fs.openSync(file, 'r');
  const chunk = Buffer.alloc(64 * 1024);
  let text = '';
  try {
    for (;;) {
      const read = fs.readSync(descriptor, chunk, 0, chunk.length, null);
      if (read === 0) return null;
      text += chunk.toString('utf8', 0, read);
      const match = /"cwd":"((?:[^"\\]|\\.)*)"/.exec(text);
      if (match) return JSON.parse(`"${match[1]}"`);
      if (text.length > 8 * 1024 * 1024) return null;
    }
  } finally {
    fs.closeSync(descriptor);
  }
}

function walk(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(full));
    else if (entry.isFile()) files.push(full);
  }
  return files;
}

function parseLines(buffer) {
  const records = [];
  for (const line of buffer.toString('utf8').split('\n')) {
    if (!line.trim()) continue;
    try {
      records.push(JSON.parse(line));
    } catch {
      records.push({ type: 'unparseable' });
    }
  }
  return records;
}

function clip(text, limit) {
  if (text.length <= limit) return text;
  return `${text.slice(0, limit)}\n[... ${text.length - limit} more characters, see raw]`;
}

function blockText(content) {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';
  return content.map((block) => (block.type === 'text' ? block.text : `[${block.type}]`)).join('\n');
}

function summarize(records) {
  const summary = {
    title: null, cwd: null, firstTimestamp: null, lastTimestamp: null,
    models: new Set(), versions: new Set(), branches: new Set(),
    userTurns: 0, assistantMessages: 0, toolCalls: 0, unparseableLines: 0,
  };
  for (const record of records) {
    if (record.type === 'unparseable') summary.unparseableLines++;
    if (record.type === 'ai-title') summary.title = record.aiTitle;
    if (record.cwd && !summary.cwd) summary.cwd = record.cwd;
    if (record.version) summary.versions.add(record.version);
    if (record.gitBranch) summary.branches.add(record.gitBranch);
    if (record.timestamp && (record.type === 'user' || record.type === 'assistant')) {
      summary.firstTimestamp ??= record.timestamp;
      summary.lastTimestamp = record.timestamp;
    }
    if (record.type === 'assistant') {
      summary.assistantMessages++;
      const model = record.message?.model;
      if (model && model !== '<synthetic>') summary.models.add(model);
      for (const block of record.message?.content ?? []) if (block.type === 'tool_use') summary.toolCalls++;
    }
    if (record.type === 'user' && !record.isMeta) {
      const content = record.message?.content;
      const typed = typeof content === 'string' || (Array.isArray(content) && content.some((block) => block.type === 'text'));
      if (typed) summary.userTurns++;
    }
  }
  return {
    ...summary,
    models: [...summary.models], versions: [...summary.versions], branches: [...summary.branches],
  };
}

function render(records, heading) {
  const lines = [...heading, ''];
  const toolNames = new Map();
  const stamp = (record) => (record.timestamp ? `[${record.timestamp}] ` : '');
  const say = (record, label, text) => lines.push(`${stamp(record)}${label}`, text, '');

  for (const record of records) {
    const content = record.message?.content;
    if (record.type === 'user') {
      const label = record.isCompactSummary ? 'COMPACTION SUMMARY' : record.isMeta ? 'USER (meta)' : 'USER';
      if (typeof content === 'string') {
        say(record, label, content);
      } else if (Array.isArray(content)) {
        for (const block of content) {
          if (block.type === 'text') say(record, label, block.text);
          else if (block.type === 'tool_result') {
            const name = toolNames.get(block.tool_use_id) ?? 'tool';
            const failed = block.is_error ? ' (error)' : '';
            say(record, `RESULT ${name}${failed}`, clip(blockText(block.content), RESULT_LIMIT));
          } else lines.push(`${stamp(record)}USER [${block.type}]`, '');
        }
      }
    } else if (record.type === 'assistant' && Array.isArray(content)) {
      for (const block of content) {
        if (block.type === 'text') say(record, 'ASSISTANT', block.text);
        else if (block.type === 'thinking' && block.thinking) say(record, 'ASSISTANT (thinking)', block.thinking);
        else if (block.type === 'tool_use') {
          toolNames.set(block.id, block.name);
          say(record, `TOOL ${block.name}`, clip(JSON.stringify(block.input, null, 2) ?? '', INPUT_LIMIT));
        }
      }
    } else if (record.type === 'system' && typeof record.content === 'string' && record.subtype !== 'turn_duration') {
      say(record, `SYSTEM (${record.subtype})`, record.content);
    }
  }
  return lines.join('\n');
}

const CRC_TABLE = new Uint32Array(256).map((_, index) => {
  let value = index;
  for (let bit = 0; bit < 8; bit++) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
  return value >>> 0;
});

function crc32(buffer) {
  if (typeof zlib.crc32 === 'function') return zlib.crc32(buffer);
  let value = 0xffffffff;
  for (const byte of buffer) value = CRC_TABLE[(value ^ byte) & 0xff] ^ (value >>> 8);
  return (value ^ 0xffffffff) >>> 0;
}

class ZipWriter {
  constructor(file) {
    this.descriptor = fs.openSync(file, 'w');
    this.offset = 0;
    this.entries = [];
  }

  write(buffer) {
    fs.writeSync(this.descriptor, buffer);
    this.offset += buffer.length;
  }

  add(name, data, modified = new Date()) {
    if (data.length >= 0xffffffff || this.offset >= 0xffffffff || this.entries.length >= 0xfffe) {
      throw new Error('Archive exceeds the limits of the plain zip format.');
    }
    const nameBytes = Buffer.from(name, 'utf8');
    const deflated = zlib.deflateRawSync(data, { level: 9 });
    const stored = deflated.length >= data.length;
    const body = stored ? data : deflated;
    const year = Math.max(modified.getFullYear(), 1980);
    const entry = {
      nameBytes, method: stored ? 0 : 8, crc: crc32(data), packed: body.length, size: data.length, offset: this.offset,
      time: (modified.getHours() << 11) | (modified.getMinutes() << 5) | (modified.getSeconds() >> 1),
      date: ((year - 1980) << 9) | ((modified.getMonth() + 1) << 5) | modified.getDate(),
    };
    const header = Buffer.alloc(30);
    header.writeUInt32LE(0x04034b50, 0);
    header.writeUInt16LE(20, 4);
    header.writeUInt16LE(0x0800, 6);
    header.writeUInt16LE(entry.method, 8);
    header.writeUInt16LE(entry.time, 10);
    header.writeUInt16LE(entry.date, 12);
    header.writeUInt32LE(entry.crc, 14);
    header.writeUInt32LE(entry.packed, 18);
    header.writeUInt32LE(entry.size, 22);
    header.writeUInt16LE(nameBytes.length, 26);
    this.write(header);
    this.write(nameBytes);
    this.write(body);
    this.entries.push(entry);
  }

  close() {
    const start = this.offset;
    for (const entry of this.entries) {
      const header = Buffer.alloc(46);
      header.writeUInt32LE(0x02014b50, 0);
      header.writeUInt16LE(20, 4);
      header.writeUInt16LE(20, 6);
      header.writeUInt16LE(0x0800, 8);
      header.writeUInt16LE(entry.method, 10);
      header.writeUInt16LE(entry.time, 12);
      header.writeUInt16LE(entry.date, 14);
      header.writeUInt32LE(entry.crc, 16);
      header.writeUInt32LE(entry.packed, 20);
      header.writeUInt32LE(entry.size, 24);
      header.writeUInt16LE(entry.nameBytes.length, 28);
      header.writeUInt32LE(entry.offset, 42);
      this.write(header);
      this.write(entry.nameBytes);
    }
    const end = Buffer.alloc(22);
    end.writeUInt32LE(0x06054b50, 0);
    end.writeUInt16LE(this.entries.length, 8);
    end.writeUInt16LE(this.entries.length, 10);
    end.writeUInt32LE(this.offset - start, 12);
    end.writeUInt32LE(start, 16);
    this.write(end);
    fs.closeSync(this.descriptor);
  }
}

const startDirectory = path.resolve(argument('--repo') ?? process.cwd());
const repoRoot = realPath(git(['rev-parse', '--show-toplevel'], startDirectory) || startDirectory);
const configDirectory = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude');
const projectsDirectory = path.join(configDirectory, 'projects');
const outDirectory = path.resolve(argument('--out') ?? path.join(repoRoot, '.workspace', 'export'));

if (!fs.existsSync(projectsDirectory)) {
  console.error(`No Claude Code sessions found: ${projectsDirectory} does not exist.`);
  process.exit(1);
}

const usedNames = new Set();
function shortName(relative) {
  const base = relative === '' ? '_root' : relative.split(path.sep).join('-');
  let name = base;
  for (let suffix = 2; usedNames.has(name); suffix++) name = `${base}-${suffix}`;
  usedNames.add(name);
  return name;
}

const folders = [];
for (const entry of fs.readdirSync(projectsDirectory, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  const folder = path.join(projectsDirectory, entry.name);
  const sessions = fs.readdirSync(folder).filter((name) => name.endsWith('.jsonl'));
  for (const session of sessions) {
    const cwd = firstWorkingDirectory(path.join(folder, session));
    if (!cwd) continue;
    const inside = [cwd, realPath(cwd)].find((candidate) => isInside(repoRoot, candidate));
    if (inside) folders.push({ key: entry.name, folder, sessions, name: shortName(path.relative(repoRoot, inside)) });
    break;
  }
}

if (folders.length === 0) {
  console.error(`No Claude Code sessions are recorded for ${repoRoot}.`);
  process.exit(1);
}

const userName = git(['config', 'user.name'], repoRoot) || os.userInfo().username;
const userEmail = git(['config', 'user.email'], repoRoot);
const now = new Date();
const pad = (value) => String(value).padStart(2, '0');
const stampText = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`;
const slug = userName.normalize('NFKD').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '').toLowerCase() || 'student';

fs.mkdirSync(outDirectory, { recursive: true });
const zipPath = path.join(outDirectory, `${slug}-${stampText}.zip`);
const zip = new ZipWriter(zipPath);
const manifest = {
  scriptVersion: SCRIPT_VERSION, generatedAt: now.toISOString(), repoRoot, platform: process.platform,
  node: process.version, gitUserName: userName, gitUserEmail: userEmail, folders: [],
};
let rawBytes = 0;

for (const { key, folder, sessions, name } of folders) {
  const folderEntry = { name, key, sessions: [] };
  for (const file of walk(folder)) {
    const relative = path.relative(folder, file).split(path.sep);
    if (relative[0] === 'memory') continue;
    const data = fs.readFileSync(file);
    rawBytes += data.length;
    zip.add(['raw', name, ...relative].join('/'), data, fs.statSync(file).mtime);
  }
  for (const session of sessions.sort()) {
    const sessionId = session.replace(/\.jsonl$/, '');
    const data = fs.readFileSync(path.join(folder, session));
    const records = parseLines(data);
    const summary = summarize(records);
    const sessionEntry = { sessionId, bytes: data.length, ...summary, subagents: [], toolResultFiles: 0 };
    zip.add(['readable', name, `${sessionId}.txt`].join('/'), Buffer.from(render(records, [
      `Session: ${sessionId}`, `Title: ${summary.title ?? ''}`, `Working directory: ${summary.cwd ?? ''}`,
      `From: ${summary.firstTimestamp ?? ''}  To: ${summary.lastTimestamp ?? ''}`,
      `Model: ${summary.models.join(', ')}  Claude Code: ${summary.versions.join(', ')}`,
    ]), 'utf8'));

    const subagentDirectory = path.join(folder, sessionId, 'subagents');
    if (fs.existsSync(subagentDirectory)) {
      for (const agentFile of fs.readdirSync(subagentDirectory).filter((entry) => entry.endsWith('.jsonl')).sort()) {
        const agentData = fs.readFileSync(path.join(subagentDirectory, agentFile));
        const agentRecords = parseLines(agentData);
        const agentSummary = summarize(agentRecords);
        const agentId = agentFile.replace(/\.jsonl$/, '');
        let meta = {};
        try {
          meta = JSON.parse(fs.readFileSync(path.join(subagentDirectory, `${agentId}.meta.json`), 'utf8'));
        } catch {
          meta = {};
        }
        sessionEntry.subagents.push({
          agentId, agentType: meta.agentType ?? null, description: meta.description ?? null, bytes: agentData.length,
          firstTimestamp: agentSummary.firstTimestamp, lastTimestamp: agentSummary.lastTimestamp,
          models: agentSummary.models, assistantMessages: agentSummary.assistantMessages, toolCalls: agentSummary.toolCalls,
        });
        zip.add(['readable', name, sessionId, `${agentId}.txt`].join('/'), Buffer.from(render(agentRecords, [
          `Subagent: ${agentId}`, `Parent session: ${sessionId}`, `Type: ${meta.agentType ?? ''}`,
          `Description: ${meta.description ?? ''}`,
        ]), 'utf8'));
      }
    }
    const toolResultDirectory = path.join(folder, sessionId, 'tool-results');
    if (fs.existsSync(toolResultDirectory)) sessionEntry.toolResultFiles = fs.readdirSync(toolResultDirectory).length;
    folderEntry.sessions.push(sessionEntry);
  }
  manifest.folders.push(folderEntry);
}

manifest.workspace = {};
for (const folderName of WORKSPACE_FOLDERS) {
  const directory = path.join(repoRoot, '.workspace', folderName);
  const files = fs.existsSync(directory) ? walk(directory) : [];
  for (const file of files) {
    const relative = path.relative(directory, file).split(path.sep);
    zip.add(['workspace', folderName, ...relative].join('/'), fs.readFileSync(file), fs.statSync(file).mtime);
  }
  manifest.workspace[folderName] = files.length;
}

zip.add('manifest.json', Buffer.from(JSON.stringify(manifest, null, 2), 'utf8'));
zip.close();

const megabytes = (bytes) => (bytes / 1024 / 1024).toFixed(1);
for (const folder of manifest.folders) console.log(`${folder.name}: ${folder.sessions.length} sessions`);
for (const folderName of WORKSPACE_FOLDERS) console.log(`.workspace/${folderName}: ${manifest.workspace[folderName]} files`);
console.log(`Raw size: ${megabytes(rawBytes)} MB, archive: ${megabytes(fs.statSync(zipPath).size)} MB`);
console.log(zipPath);
