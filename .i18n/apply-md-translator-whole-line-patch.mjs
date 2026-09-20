import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.argv[2];
if (!root) {
  console.error("usage: node apply-md-translator-whole-line-patch.mjs <md-translator-dir>");
  process.exit(2);
}

const target = join(root, "src/app/lib/translation/cliFormat.ts");
const source = readFileSync(target, "utf8");
const marker = "    const { contentLines, sourceLineNumbers } = parsed;\n\n    // 结构化模式:";

if (!source.includes(marker)) {
  console.error("Pinned md-translator source no longer matches the PoC patch point.");
  process.exit(1);
}

const injected = [
  "    const { contentLines, sourceLineNumbers } = parsed;",
  "",
  "    // README i18n whole-line mode (LLM only):",
  "    // keep md-translator's placeholder protection, but send each protected line as",
  "    // one unit so the model can choose natural target-language word order around",
  "    // inline code / links. Hard-fail if any placeholder is lost, duplicated,",
  "    // or rewritten. Token order may change when target-language grammar requires it;",
  "    if (ctx.isLlmMethod && contentLines.length > 0) {",
  "      const outcome = await ctx.translate(contentLines, undefined, { lineNumbers: sourceLineNumbers, fileName: ctx.fileName });",
  "      const softFilled = softFilledIndices(outcome);",
  "      const cleanedLines = mapSkippingSoftFilled(outcome.lines, softFilled, (line) => applyRemoveCharsToMarkdown(line, ctx.removeChars));",
  "      const tokenPattern = /<<<[A-Z_]+_\\d+>>>/g;",
  "",
  "      for (let i = 0; i < contentLines.length; i++) {",
  "        const expected = contentLines[i].match(tokenPattern) ?? [];",
  "        const actual = cleanedLines[i].match(tokenPattern) ?? [];",
  "        if (expected.length !== actual.length || expected.some((token, n) => token !== actual[n])) {",
  "          const line = sourceLineNumbers[i] ?? i + 1;",
  "          throw new CliFileFormatError(\"protected Markdown token mismatch at source line \" + line);",
  "        }",
  "      }",
  "",
  "      return { content: restorePlaceholders(cleanedLines.join(\"\\n\"), parsed), ext };",
  "    }",
  "",
  "    // 構造化モード:"
].join("\n");

writeFileSync(target, source.replace(marker, injected), "utf8");
console.log("Applied README i18n whole-line Markdown patch.");
