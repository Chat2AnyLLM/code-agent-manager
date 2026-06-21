package metadata

// Item represents a single searchable/installable metadata record.
type Item struct {
	ID               int64  `json:"id"`
	Kind             string `json:"kind"`
	Name             string `json:"name"`
	Description      string `json:"description"`
	SourceID         int64  `json:"source_id"`
	RepoOwner        string `json:"repo_owner"`
	RepoName         string `json:"repo_name"`
	RepoBranch       string `json:"repo_branch"`
	ItemPath         string `json:"item_path"`
	InstallKey       string `json:"install_key"`
	TargetApps       string `json:"target_apps"`
	MetadataJSON     string `json:"metadata_json"`
	Installed        bool     `json:"installed"`
	InstalledTargets string   `json:"installed_targets"`
	InstalledApps    []string `json:"installed_apps,omitempty"`
	Content          string   `json:"content"`
	ContentCachedAt  string   `json:"content_cached_at"`
	ManifestPath     string   `json:"manifest_path"`
	LastSeenAt       string   `json:"last_seen_at"`
	CreatedAt        string   `json:"created_at"`
	UpdatedAt        string   `json:"updated_at"`
}

// Source represents a configured metadata repository source.
type Source struct {
	ID              int64  `json:"id"`
	Kind            string `json:"kind"`
	SourceKey       string `json:"source_key"`
	Owner           string `json:"owner"`
	Repo            string `json:"repo"`
	Branch          string `json:"branch"`
	Path            string `json:"path"`
	Enabled         bool   `json:"enabled"`
	SourceFile      string `json:"source_file"`
	LastRefreshedAt string `json:"last_refreshed_at"`
	CreatedAt       string `json:"created_at"`
	UpdatedAt       string `json:"updated_at"`
}

// SearchQuery configures a metadata search.
type SearchQuery struct {
	Query  string `json:"query"`
	Kind   string `json:"kind"`
	Limit  int    `json:"limit"`
	Offset int    `json:"offset"`
}

// SearchResponse is a paginated search result set.
type SearchResponse struct {
	Items []Item `json:"items"`
	Total int    `json:"total"`
	Limit int    `json:"limit"`
	Offset int   `json:"offset"`
}

// RefreshSummary reports the result of a refresh operation.
type RefreshSummary struct {
	SourcesScanned int      `json:"sources_scanned"`
	ItemsAdded     int      `json:"items_added"`
	ItemsUpdated   int      `json:"items_updated"`
	ItemsStale     int      `json:"items_stale"`
	FailedSources  []string `json:"failed_sources"`
}
