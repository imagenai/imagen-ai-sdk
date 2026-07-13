package imagen

// PhotographyType selects AI optimization tuned to a shoot type.
type PhotographyType string

const (
	PhotographyTypeNoType          PhotographyType = "NO_TYPE"
	PhotographyTypeOther           PhotographyType = "OTHER"
	PhotographyTypePortraits       PhotographyType = "PORTRAITS"
	PhotographyTypeWedding         PhotographyType = "WEDDING"
	PhotographyTypeRealEstate      PhotographyType = "REAL_ESTATE"
	PhotographyTypeLandscapeNature PhotographyType = "LANDSCAPE_NATURE"
	PhotographyTypeEvents          PhotographyType = "EVENTS"
	PhotographyTypeFamilyNewborn   PhotographyType = "FAMILY_NEWBORN"
	PhotographyTypeBoudoir         PhotographyType = "BOUDOIR"
	PhotographyTypeSports          PhotographyType = "SPORTS"
	PhotographyTypeSchool          PhotographyType = "SCHOOL"
)

// CropAspectRatio is the target aspect ratio when cropping is enabled.
type CropAspectRatio string

const (
	CropAspectRatio2x3 CropAspectRatio = "2X3"
	CropAspectRatio4x5 CropAspectRatio = "4X5"
	CropAspectRatio5x7 CropAspectRatio = "5X7"
)

// DNGCompression controls compression of HDR-merged DNG output.
type DNGCompression string

const (
	DNGCompressionLossy    DNGCompression = "LOSSY"
	DNGCompressionLossless DNGCompression = "LOSSLESS"
)

// ProjectSource identifies which project family an enhancement/copilot call
// targets. It is required in enhance, copilot, reset and finalize request bodies.
type ProjectSource string

const (
	ProjectSourceRegular ProjectSource = "REGULAR"
	ProjectSourceI2I     ProjectSource = "I2I"
)
