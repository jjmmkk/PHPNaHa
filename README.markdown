# PHPNaHa

PHP namespace handler package for Sublime Text.

## Usage notes

To enable the lookup commands, you must first index your project folders. This is done by the index command, _PHPNaHa: Index project_.

## Commands

All command palette names are prefixed with _PHPNaHa:_

### Index project

This command makes an index containing all namespaces. For projects with <5000 classes, it should finish swiftly. For the 10k+ class projects, it might need several seconds.

#### Key binding

None by default. Can be bound with the following:

```json
[
    { "keys": ["KEY(S)"], "command": "phpnaha_index_project_namespaces" }
	]
```

### Insert namespace statement

Inserts namespace into current file, if applicable.

#### Key binding

None by default. Can be bound with the following:

```json
[
    { "keys": ["KEY(S)"], "command": "phpnaha_insert_namespace_statement" }
]
```

### Copy namespace and class

Puts the namespace and class name into the clipboard.

#### Key binding

None by default. Can be bound with the following:

```json
[
    { "keys": ["KEY(S)"], "command": "phpnaha_copy_namespace_and_class" }
]
```

### Open class file

Open the file containing the selected class name or namespace. You select a class name or namespace by setting the cursor in it or highlighting it. If more than one matching file is found, a quick panel will be displayed with the files as options.

#### Key binding

None by default. Can be bound with the following:

```json
[
    { "keys": ["KEY(S)"], "command": "phpnaha_open_class_file" }
]
```

### Find class and insert use statement

If the cursor is inside a word or a word is highlighted, a matching class will be looked for. If more than one matching file is found, a quick panel will be displayed with the files as options.

If the cursor is on a blank line or outside a word, all indexes class files will be displayed in a quick panel.

Selecting a file will insert a `use` statement in the current file.

#### Key binding

Default key binding:

```json
[
    { "keys": ["ctrl+i"], "command": "phpnaha_find_class_and_insert_use_statement" }
]
```

## Todo

* Stop folders
