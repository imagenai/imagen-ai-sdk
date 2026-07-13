package imagen

import "testing"

// TestRAWExtensionsParity pins the RAW extension set to the reference Python/Node
// SDKs so it cannot silently drift and cause clients to accept/skip different files.
func TestRAWExtensionsParity(t *testing.T) {
	// Exact set from sdks/python/imagen_sdk/imagen_sdk.py RAW_EXTENSIONS.
	want := []string{
		".dng", ".nef", ".cr2", ".arw", ".nrw", ".crw", ".srf", ".sr2", ".orf",
		".raw", ".rw2", ".raf", ".ptx", ".pef", ".rwl", ".srw", ".cr3", ".3fr", ".fff",
	}
	if len(RAWExtensions) != len(want) {
		t.Fatalf("RAWExtensions has %d entries, want %d", len(RAWExtensions), len(want))
	}
	for _, ext := range want {
		if !RAWExtensions[ext] {
			t.Errorf("RAWExtensions missing %q", ext)
		}
	}
}

func TestCheckUniqueBaseNames(t *testing.T) {
	if err := checkUniqueBaseNames([]string{"/a/img.dng", "/b/other.dng"}); err != nil {
		t.Errorf("unique base names should pass: %v", err)
	}
	// Same base name from different directories must be rejected.
	if err := checkUniqueBaseNames([]string{"/a/img.dng", "/b/img.dng"}); err == nil {
		t.Error("expected error for colliding base names")
	}
}

func TestCheckFilesMatchProfileType(t *testing.T) {
	rawProfile := Profile{ImageType: "RAW"}
	if err := CheckFilesMatchProfileType(rawProfile, []string{"a.dng", "b.cr3"}); err != nil {
		t.Errorf("RAW files against RAW profile: %v", err)
	}
	if err := CheckFilesMatchProfileType(rawProfile, []string{"a.dng", "b.jpg"}); err == nil {
		t.Error("expected mismatch for jpg against RAW profile")
	}
	// Empty ImageType accepts anything.
	if err := CheckFilesMatchProfileType(Profile{}, []string{"a.jpg", "b.dng"}); err != nil {
		t.Errorf("empty profile type should accept any: %v", err)
	}
}
