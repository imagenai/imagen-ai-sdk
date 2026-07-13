package imagen

import "path/filepath"

// baseName returns the final path element of p.
func baseName(p string) string { return filepath.Base(p) }

// ceilDiv returns ceil(a/b) for positive b.
func ceilDiv(a, b int64) int64 {
	if b <= 0 {
		return a
	}
	return (a + b - 1) / b
}

func maxInt64(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}
