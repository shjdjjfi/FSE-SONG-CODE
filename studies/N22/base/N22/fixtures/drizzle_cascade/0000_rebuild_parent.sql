PRAGMA foreign_keys=OFF;
--> statement-breakpoint
CREATE TABLE `__new_parent` (
    `id` TEXT PRIMARY KEY NOT NULL,
    `mode` TEXT NOT NULL DEFAULT 'markup'
);
--> statement-breakpoint
INSERT INTO `__new_parent` (`id`, `mode`) SELECT `id`, `mode` FROM `parent`;
--> statement-breakpoint
DROP TABLE `parent`;
--> statement-breakpoint
ALTER TABLE `__new_parent` RENAME TO `parent`;
--> statement-breakpoint
PRAGMA foreign_keys=ON;
