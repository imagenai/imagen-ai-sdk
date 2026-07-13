package imagen

// Bool returns a pointer to v. Optional fields (e.g. on EditOptions) are pointers
// so that "unset" is distinct from "false" and is omitted from the JSON payload.
func Bool(v bool) *bool { return &v }

// Int returns a pointer to v.
func Int(v int) *int { return &v }

// String returns a pointer to v.
func String(v string) *string { return &v }
