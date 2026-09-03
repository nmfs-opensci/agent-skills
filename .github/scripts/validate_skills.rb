#!/usr/bin/env ruby
# frozen_string_literal: true

require "pathname"
require "psych"
require "yaml"

ROOT = Pathname.new(__dir__).join("../..").expand_path
SKILLS = ROOT.join("skills")
EVALS = ROOT.join("evals")
NAME_PATTERN = /\A[a-z0-9]+(?:-[a-z0-9]+)*\z/
SECRET_PATTERNS = {
  "private key" => /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/,
  "AWS access key" => /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/,
  "GitHub token" => /\bgh[pousr]_[A-Za-z0-9]{36,255}\b/,
  "Slack token" => /\bxox[baprs]-[A-Za-z0-9-]{20,}\b/,
  "OpenAI API key" => /\bsk-[A-Za-z0-9_-]{20,}\b/,
  "Google API key" => /\bAIza[A-Za-z0-9_-]{35}\b/
}.freeze

def relative(path)
  path.relative_path_from(ROOT)
end

def parse_frontmatter(path)
  lines = path.read(encoding: "UTF-8").lines(chomp: true)
  return [{}, ["#{relative(path)}: YAML frontmatter must come first"]] if lines.empty? || lines.first != "---"

  closing = lines[1..]&.index("---")
  return [{}, ["#{relative(path)}: YAML frontmatter is not closed"]] unless closing

  yaml = lines[1..closing].join("\n")
  document = Psych.parse(yaml)
  fields = YAML.safe_load(yaml, permitted_classes: [], permitted_symbols: [], aliases: false)
  errors = []

  unless document&.root.is_a?(Psych::Nodes::Mapping) && fields.is_a?(Hash)
    return [{}, ["#{relative(path)}: frontmatter must be a YAML mapping"]]
  end

  keys = document.root.children.each_slice(2).filter_map do |key, _value|
    key.value if key.is_a?(Psych::Nodes::Scalar)
  end
  keys.tally.select { |_key, count| count > 1 }.each_key do |key|
    errors << "#{relative(path)}: duplicate field '#{key}'"
  end

  unsupported = fields.keys.reject { |key| %w[name description].include?(key) }
  unless unsupported.empty?
    errors << "#{relative(path)}: unsupported frontmatter field(s): #{unsupported.map(&:inspect).sort.join(', ')}"
  end

  %w[name description].each do |required|
    unless fields[required].is_a?(String) && !fields[required].strip.empty?
      errors << "#{relative(path)}: missing or invalid frontmatter field '#{required}'"
    end
  end
  [fields, errors]
rescue Errno::ENOENT, EncodingError, Psych::Exception => e
  [{}, ["#{relative(path)}: invalid YAML frontmatter (#{e.message.lines.first.strip})"]]
end

def validate_skills
  return [] unless SKILLS.exist?

  errors = []
  SKILLS.children.select(&:directory?).sort.each do |skill_dir|
    skill_file = skill_dir.join("SKILL.md")
    all_skill_files = skill_dir.glob("**/SKILL.md")
    unless skill_file.file?
      errors << "#{relative(skill_dir)}: missing SKILL.md"
      next
    end
    errors << "#{relative(skill_dir)}: must contain exactly one SKILL.md" unless all_skill_files.length == 1

    fields, frontmatter_errors = parse_frontmatter(skill_file)
    errors.concat(frontmatter_errors)
    name = fields["name"]
    if name.is_a?(String)
      errors << "#{relative(skill_file)}: invalid skill name '#{name}'" unless NAME_PATTERN.match?(name)
      errors << "#{relative(skill_file)}: name exceeds 64 characters" if name.length > 64
      if name != skill_dir.basename.to_s
        errors << "#{relative(skill_file)}: name '#{name}' does not match directory '#{skill_dir.basename}'"
      end
    end
    description = fields["description"]
    if description.is_a?(String) && description.length > 1024
      errors << "#{relative(skill_file)}: description exceeds 1024 characters"
    end
    unless NAME_PATTERN.match?(skill_dir.basename.to_s)
      errors << "#{relative(skill_dir)}: directory name must use lowercase letters, digits, and single hyphens"
    end
  end
  errors
end

def validate_evaluations
  return [] unless EVALS.exist?

  EVALS.children.select(&:directory?).sort.filter_map do |evaluation|
    "#{relative(evaluation)}: no corresponding skill" unless SKILLS.join(evaluation.basename, "SKILL.md").file?
  end
end

def scan_for_secrets
  ROOT.glob("**/*", File::FNM_DOTMATCH).select(&:file?).sort.flat_map do |path|
    next [] if path.each_filename.include?(".git")

    begin
      content = path.read(encoding: "UTF-8")
    rescue EncodingError, SystemCallError
      next []
    end
    SECRET_PATTERNS.filter_map do |label, pattern|
      "#{relative(path)}: possible #{label}" if pattern.match?(content)
    end
  end
end

errors = validate_skills + validate_evaluations + scan_for_secrets
if errors.empty?
  puts "Skill validation passed."
  exit 0
end

warn "Skill validation failed:"
errors.each { |error| warn "- #{error}" }
exit 1
