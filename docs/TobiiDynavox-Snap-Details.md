Exports are .sps files. these are sqlite files. no encryption. 


here is the sttructre

ERD Diagram here : https://dbdiagram.io/d/TobiiDynavoxSnap-651a8680ffbf5169f0da45d5

```sql

BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "CommandSequence" (
	"Id"	integer NOT NULL,
	"SerializedCommands"	varchar,
	"ButtonId"	integer,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "ButtonPlacement" (
	"Id"	integer NOT NULL,
	"GridPosition"	varchar,
	"Visible"	integer,
	"ButtonId"	integer,
	"PageLayoutId"	integer,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "PageLayout" (
	"Id"	integer NOT NULL,
	"PageLayoutSetting"	varchar,
	"PageId"	integer,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "PageExtra" (
	"Id"	integer,
	"AccessedAt"	bigint,
	PRIMARY KEY("Id"),
	FOREIGN KEY("Id") REFERENCES "Page"("Id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "PageSetData" (
	"Id"	integer NOT NULL,
	"Identifier"	varchar,
	"Data"	blob,
	"RefCount"	integer DEFAULT 0,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "SyncData" (
	"UniqueId"	varchar(36) NOT NULL,
	"Type"	integer,
	"Timestamp"	bigint,
	"SyncHash"	integer,
	"Deleted"	integer,
	"Description"	VARCHAR,
	PRIMARY KEY("UniqueId")
);
CREATE TABLE IF NOT EXISTS "Synchronization" (
	"Id"	integer NOT NULL,
	"SyncServerIdentifier"	varchar,
	"PageSetTimestamp"	bigint,
	"PageSetSyncHash"	integer,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "Page" (
	"Id"	integer NOT NULL,
	"UniqueId"	varchar(36),
	"Title"	varchar,
	"PageType"	integer,
	"Language"	varchar,
	"BackgroundColor"	integer,
	"ContentTag"	varchar,
	"Timestamp"	bigint,
	"SyncHash"	integer,
	"LibrarySymbolId"	integer,
	"PageSetImageId"	integer,
	"GridDimension"	varchar,
	"MessageBarVisible"	integer,
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "PageSetProperties" (
	"Id"	integer,
	"ContentIdentifier"	VARCHAR,
	"ContentVersion"	VARCHAR,
	"SchemaVersion"	VARCHAR,
	"UniqueId"	VARCHAR(36),
	"Language"	VARCHAR,
	"Timestamp"	BIGINT,
	"SyncHash"	integer,
	"DefaultHomePageUniqueId"	VARCHAR(36),
	"SerializedHomePageUniqueIdOverrides"	BLOB,
	"DefaultKeyboardPageUniqueId"	VARCHAR(36),
	"SerializedKeyboardPageUniqueIdOverrides"	BLOB,
	"ToolBarUniqueId"	VARCHAR(36),
	"DashboardUniqueId"	VARCHAR(36),
	"MessageBarUniqueId"	VARCHAR(36),
	"MessageBarVisible"	integer,
	"ToolBarVisible"	integer,
	"FriendlyName"	VARCHAR,
	"Description"	VARCHAR,
	"IconImageId"	integer,
	"SerializedPreferredGridDimensions"	VARCHAR,
	"GridDimension"	VARCHAR,
	"SmartSymLayout"	integer,
	"FontFamily"	VARCHAR,
	"FontSize"	float,
	"FontStyle"	int,
	"PageBackgroundColor"	integer,
	"MessageBarBackgroundColor"	integer,
	"ToolBarBackgroundColor"	integer,
	"MessageWindowTextColor"	integer,
	"MessageWindowFontSize"	float,
	PRIMARY KEY("Id")
);
CREATE TABLE IF NOT EXISTS "ButtonPageLink" (
	"Id"	INTEGER NOT NULL,
	"ButtonId"	INTEGER NOT NULL,
	"PageUniqueId"	varchar(36) NOT NULL,
	PRIMARY KEY("Id" AUTOINCREMENT),
	FOREIGN KEY("ButtonId") REFERENCES "Button"("Id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "Button" (
	"Id"	INTEGER NOT NULL,
	"Language"	varchar,
	"Label"	varchar,
	"LabelOwnership"	integer,
	"Message"	varchar,
	"AudioCue"	varchar,
	"ImageOwnership"	integer,
	"LabelColor"	integer,
	"BackgroundColor"	integer,
	"BorderColor"	integer,
	"BorderThickness"	float,
	"FontSize"	float,
	"FontFamily"	varchar,
	"FontStyle"	integer,
	"SmartSymLayout"	integer,
	"CommandFlags"	integer,
	"ContentType"	integer,
	"ContentTag"	varchar,
	"LibrarySymbolId"	integer,
	"PageSetImageId"	integer,
	"SerializedContentTypeHandler"	varchar,
	"MessageRecordingId"	integer,
	"AudioCueRecordingId"	integer,
	"PageId"	integer,
	"UseMessageRecording"	integer,
	"UseAudioCueRecording"	integer,
	"UniqueId"	varchar(36),
	PRIMARY KEY("Id" AUTOINCREMENT)
);
CREATE INDEX IF NOT EXISTS "CommandSequence_ButtonId" ON "CommandSequence" (
	"ButtonId"
);
CREATE INDEX IF NOT EXISTS "ButtonPlacement_PageLayoutId" ON "ButtonPlacement" (
	"PageLayoutId"
);
CREATE INDEX IF NOT EXISTS "PageLayout_PageId" ON "PageLayout" (
	"PageId"
);
CREATE INDEX IF NOT EXISTS "Button_AudioCueRecordingId" ON "Button" (
	"AudioCueRecordingId"
);
CREATE INDEX IF NOT EXISTS "Button_MessageRecordingId" ON "Button" (
	"MessageRecordingId"
);
CREATE INDEX IF NOT EXISTS "Button_PageId" ON "Button" (
	"PageId"
);
CREATE INDEX IF NOT EXISTS "Button_PageSetImageId" ON "Button" (
	"PageSetImageId"
);
CREATE UNIQUE INDEX IF NOT EXISTS "PageSetData_Identifier" ON "PageSetData" (
	"Identifier"
);
CREATE UNIQUE INDEX IF NOT EXISTS "Page_UniqueId" ON "Page" (
	"UniqueId"
);
CREATE INDEX IF NOT EXISTS "Page_PageSetImageId" ON "Page" (
	"PageSetImageId"
);
COMMIT;

```

DBML 
```dbml
Table CommandSequence {
  Id int [pk, not null]
  SerializedCommands varchar
  ButtonId int
}

Table ButtonPlacement {
  Id int [pk, not null]
  GridPosition varchar
  Visible int
  ButtonId int
  PageLayoutId int
}

Table PageLayout {
  Id int [pk, not null]
  PageLayoutSetting varchar
  PageId int
}

Table PageExtra {
  Id int [pk, not null, ref: > Page.Id]
  AccessedAt bigint
}

Table PageSetData {
  Id int [pk, not null]
  Identifier varchar
  Data blob
  RefCount int [default: 0]
}

Table SyncData {
  UniqueId varchar(36) [pk, not null]
  Type int
  Timestamp bigint
  SyncHash int
  Deleted int
  Description varchar
}

Table Synchronization {
  Id int [pk, not null]
  SyncServerIdentifier varchar
  PageSetTimestamp bigint
  PageSetSyncHash int
}

Table Page {
  Id int [pk, not null]
  UniqueId varchar(36)
  Title varchar
  PageType int
  Language varchar
  BackgroundColor int
  ContentTag varchar
  Timestamp bigint
  SyncHash int
  LibrarySymbolId int
  PageSetImageId int
  GridDimension varchar
  MessageBarVisible int
}

Table PageSetProperties {
  Id int [pk, not null]
  ContentIdentifier varchar
  ContentVersion varchar
  SchemaVersion varchar
  UniqueId varchar(36)
  Language varchar
  Timestamp bigint
  SyncHash int
  DefaultHomePageUniqueId varchar(36)
  SerializedHomePageUniqueIdOverrides blob
  DefaultKeyboardPageUniqueId varchar(36)
  SerializedKeyboardPageUniqueIdOverrides blob
  ToolBarUniqueId varchar(36)
  DashboardUniqueId varchar(36)
  MessageBarUniqueId varchar(36)
  MessageBarVisible int
  ToolBarVisible int
  FriendlyName varchar
  Description varchar
  IconImageId int
  SerializedPreferredGridDimensions varchar
  GridDimension varchar
  SmartSymLayout int
  FontFamily varchar
  FontSize float
  FontStyle int
  PageBackgroundColor int
  MessageBarBackgroundColor int
  ToolBarBackgroundColor int
  MessageWindowTextColor int
  MessageWindowFontSize float
}

Table ButtonPageLink {
  Id int [pk, not null]
  ButtonId int [not null, ref: > Button.Id]
  PageUniqueId varchar(36) [not null]
}

Table Button {
  Id int [pk, not null]
  Language varchar
  Label varchar
  LabelOwnership int
  Message varchar
  AudioCue varchar
  ImageOwnership int
  LabelColor int
  BackgroundColor int
  BorderColor int
  BorderThickness float
  FontSize float
  FontFamily varchar
  FontStyle int
  SmartSymLayout int
  CommandFlags int
  ContentType int
  ContentTag varchar
  LibrarySymbolId int
  PageSetImageId int
  SerializedContentTypeHandler varchar
  MessageRecordingId int
  AudioCueRecordingId int
  PageId int
  UseMessageRecording int
  UseAudioCueRecording int
  UniqueId varchar(36)
}

// Relationships
Ref: CommandSequence.ButtonId > Button.Id
Ref: ButtonPlacement.ButtonId > Button.Id
Ref: ButtonPlacement.PageLayoutId > PageLayout.Id
Ref: PageLayout.PageId > Page.Id
Ref: PageExtra.Id > Page.Id
Ref: ButtonPageLink.ButtonId > Button.Id
Ref: Button.PageId > Page.Id

```

## Button/Language data

- There are really only two tables with this data in it `Button`- `Label` and `Button`- `Message` and `Page` - `Title`

