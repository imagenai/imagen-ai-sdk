"""
Integration and workflow tests for the Imagen AI SDK

These tests focus on end-to-end workflows and convenience functions,
testing the interaction between multiple components.

Run with: pytest test_imagen_workflow.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest

from imagen_sdk import (
    CropAspectRatio,
    EditOptions,
    ImagenClient,
    ImagenError,
    PhotographyType,
    Profile,
    ProjectError,
    QuickEditResult,
    UploadError,
    UploadResult,
    UploadSummary,
    get_profiles,
    quick_edit,
)


class WorkflowTestHelpers:
    """Helper class for workflow test data and mocks."""

    @staticmethod
    def create_sample_profiles() -> list[Profile]:
        """Create sample profile data for testing."""
        return [
            Profile(
                image_type="RAW",
                profile_key=196,
                profile_name="WARM SKIN TONES",
                profile_type="Talent",
            ),
            Profile(
                image_type="RAW",
                profile_key=254,
                profile_name="BODY LANGUAGE",
                profile_type="Talent",
            ),
            Profile(
                image_type="JPG",
                profile_key=29132,
                profile_name="MOMENTICOS",
                profile_type="Talent",
            ),
        ]

    @staticmethod
    def create_successful_upload_summary(file_count: int = 2) -> UploadSummary:
        """Create a successful upload summary for testing."""
        results = [UploadResult(file=f"image{i + 1}.jpg", success=True, error=None) for i in range(file_count)]
        return UploadSummary(total=file_count, successful=file_count, failed=0, results=results)

    @staticmethod
    def create_partial_upload_summary() -> UploadSummary:
        """Create a partially successful upload summary."""
        results = [
            UploadResult(file="image1.jpg", success=True, error=None),
            UploadResult(file="image2.jpg", success=False, error="Network timeout"),
            UploadResult(file="image3.jpg", success=True, error=None),
        ]
        return UploadSummary(total=3, successful=2, failed=1, results=results)

    @staticmethod
    def create_mock_client_for_workflow():
        """Create a mock ImagenClient for workflow testing."""
        mock_client = AsyncMock(spec=ImagenClient)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client


@pytest.fixture
def helpers():
    """Fixture providing WorkflowTestHelpers instance."""
    return WorkflowTestHelpers()


@pytest.fixture
def sample_profiles(helpers):
    """Fixture providing sample profiles."""
    return helpers.create_sample_profiles()


@pytest.fixture
def successful_upload_summary(helpers):
    """Fixture providing successful upload summary."""
    return helpers.create_successful_upload_summary()


@pytest.fixture
def partial_upload_summary(helpers):
    """Fixture providing partial upload summary."""
    return helpers.create_partial_upload_summary()


@pytest.fixture
def mock_client_factory(helpers):
    """Factory fixture for creating mock clients."""

    def _create_mock_client():
        return helpers.create_mock_client_for_workflow()

    return _create_mock_client


class TestConvenienceFunctions:
    """Test the standalone convenience functions."""

    @pytest.mark.asyncio
    async def test_get_profiles_function_success(self, sample_profiles, mock_client_factory):
        """Test the standalone get_profiles function."""
        # Mock the ImagenClient class in the imagen_sdk module where it's imported
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client_class.return_value = mock_client

            profiles = await get_profiles("test-api-key")

            assert len(profiles) == 3
            assert profiles[0].profile_name == "WARM SKIN TONES"
            assert profiles[1].profile_key == 254
            assert profiles[2].profile_type == "Talent"

            # Verify client was created and used correctly
            mock_client_class.assert_called_once_with("test-api-key", "https://api-beta.imagen-ai.com/v1")
            mock_client.get_profiles.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_profiles_function_with_custom_url(self, mock_client_factory):
        """Test get_profiles with custom base URL."""
        custom_url = "https://custom-api.example.com/v2"

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = []
            mock_client_class.return_value = mock_client

            await get_profiles("test-key", custom_url)

            mock_client_class.assert_called_once_with("test-key", custom_url)

    @pytest.mark.asyncio
    async def test_get_profiles_function_error_handling(self, mock_client_factory):
        """Test get_profiles error propagation."""
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.side_effect = ImagenError("API Error")
            mock_client_class.return_value = mock_client

            with pytest.raises(ImagenError):
                await get_profiles("invalid-key")


class TestQuickEditWorkflow:
    """Test the quick_edit convenience function and full workflows."""

    @pytest.mark.asyncio
    @pytest.mark.workflow
    async def test_quick_edit_basic_workflow(self, successful_upload_summary, mock_client_factory, sample_profiles):
        """Test the basic quick_edit workflow without export."""
        download_links = ["https://download1.com", "https://download2.com"]

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = download_links
            mock_client_class.return_value = mock_client

            result = await quick_edit(
                api_key="test-key",
                profile_key=196,
                image_paths=["img1.dng", "img2.dng"],
                project_name="Test Project",
            )

            # Verify the result
            assert isinstance(result, QuickEditResult)
            assert result.project_uuid == "test-project-uuid"
            assert result.upload_summary == successful_upload_summary
            assert result.download_links == download_links
            assert result.export_links is None

            # Verify the workflow calls
            mock_client.create_project.assert_called_once_with("Test Project")
            mock_client.upload_images.assert_called_once_with("test-project-uuid", ["img1.dng", "img2.dng"])
            mock_client.start_editing.assert_called_once_with("test-project-uuid", 196, None, edit_options=None)
            mock_client.get_download_links.assert_called_once_with("test-project-uuid")

    @pytest.mark.asyncio
    @pytest.mark.workflow
    async def test_quick_edit_with_all_options(self, successful_upload_summary, mock_client_factory, sample_profiles):
        """Test quick_edit with all available options."""
        download_links = ["https://download1.com"]
        export_links = ["https://export1.com"]

        edit_options = EditOptions(
            crop=True,
            straighten=True,
            hdr_merge=False,
            smooth_skin=True,
            subject_mask=True,
        )

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = download_links
            mock_client.export_project.return_value = None
            mock_client.get_export_links.return_value = export_links
            mock_client_class.return_value = mock_client

            result = await quick_edit(
                api_key="test-key",
                profile_key=29132,
                image_paths=["wedding1.jpg", "wedding2.jpg"],
                project_name="Wedding Photos",
                photography_type=PhotographyType.WEDDING,
                export=True,
                edit_options=edit_options,
                base_url="https://custom.api.com",
            )

            # Verify the result includes export links
            assert result.export_links == export_links

            # Verify workflow with all options
            mock_client.start_editing.assert_called_once_with(
                "test-project-uuid",
                29132,
                PhotographyType.WEDDING,
                edit_options=edit_options,
            )
            mock_client.export_project.assert_called_once_with("test-project-uuid")
            mock_client.get_export_links.assert_called_once_with("test-project-uuid")

            # Verify client created with custom URL
            mock_client_class.assert_any_call("test-key", "https://custom.api.com", logger=None, logger_level=None)

    @pytest.mark.asyncio
    async def test_quick_edit_no_successful_uploads(self, mock_client_factory, sample_profiles):
        """Test quick_edit behavior when no uploads succeed."""
        failed_upload_summary = UploadSummary(
            total=2,
            successful=0,
            failed=2,
            results=[
                UploadResult(file="img1.dng", success=False, error="File too large"),
                UploadResult(file="img2.dng", success=False, error="Network error"),
            ],
        )

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = failed_upload_summary
            mock_client_class.return_value = mock_client

            with pytest.raises(UploadError, match="no files were uploaded successfully"):
                await quick_edit(
                    api_key="test-key",
                    profile_key=196,
                    image_paths=["img1.dng", "img2.dng"],
                )

            # Verify editing was not attempted
            mock_client.start_editing.assert_not_called()
            mock_client.get_download_links.assert_not_called()

    @pytest.mark.asyncio
    async def test_quick_edit_partial_upload_success(self, partial_upload_summary, mock_client_factory, sample_profiles):
        """Test quick_edit behavior with partial upload success."""
        download_links = [
            "https://download1.com",
            "https://download3.com",
        ]  # Only successful uploads

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = partial_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = download_links
            mock_client_class.return_value = mock_client

            result = await quick_edit(
                api_key="test-key",
                profile_key=196,
                image_paths=["img1.dng", "img2.dng", "img3.dng"],
            )

            # Should proceed with editing despite partial failure
            assert result.upload_summary.successful == 2
            assert result.upload_summary.failed == 1
            assert len(result.download_links) == 2

            # Verify editing proceeded
            mock_client.start_editing.assert_called_once()
            mock_client.get_download_links.assert_called_once()

    @pytest.mark.asyncio
    async def test_quick_edit_file_profile_type_mismatch(self, mock_client_factory, sample_profiles):
        """Test quick_edit raises UploadError when file type does not match profile type (e.g., JPG file with RAW profile)."""
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client_class.return_value = mock_client

            with pytest.raises(UploadError, match="RAW profile cannot be used with JPG files"):
                await quick_edit(
                    api_key="test-key",
                    profile_key=196,  # RAW profile
                    image_paths=["img1.jpg"],  # JPG file
                )


class TestEditOptionsWorkflow:
    """Test EditOptions model integration in workflows."""

    def test_edit_options_to_api_dict(self):
        """Test EditOptions conversion to API format."""
        # Test with all options set
        options = EditOptions(
            crop=True,
            straighten=False,
            hdr_merge=True,
            portrait_crop=None,
            smooth_skin=True,
        )

        api_dict = options.to_api_dict()

        # Should exclude None values
        expected = {
            "crop": True,
            "straighten": False,
            "hdr_merge": True,
            "smooth_skin": True,
        }
        assert api_dict == expected
        assert "portrait_crop" not in api_dict

    def test_edit_options_empty(self):
        """Test EditOptions with no values set."""
        options = EditOptions()
        api_dict = options.to_api_dict()
        assert api_dict == {}

    def test_edit_options_only_none_values(self):
        """Test EditOptions with only None values."""
        options = EditOptions(
            crop=None,
            straighten=None,
            hdr_merge=None,
            portrait_crop=None,
            smooth_skin=None,
        )
        api_dict = options.to_api_dict()
        assert api_dict == {}

    def test_edit_options_new_fields(self):
        """Test EditOptions with new fields."""
        options = EditOptions(
            headshot_crop=True,
            perspective_correction=True,
            sky_replacement=True,
            sky_replacement_template_id=123,
            window_pull=True,
            crop_aspect_ratio="16:9",
            subject_mask=True,
        )

        api_dict = options.to_api_dict()

        assert api_dict["headshot_crop"] is True
        assert api_dict["perspective_correction"] is True
        assert api_dict["sky_replacement"] is True
        assert api_dict["sky_replacement_template_id"] == 123
        assert api_dict["window_pull"] is True
        assert api_dict["crop_aspect_ratio"] == "16:9"
        assert api_dict["subject_mask"] is True

    def test_edit_options_crop_mutual_exclusivity(self):
        """Test that crop options are mutually exclusive."""
        # Test crop + portrait_crop
        with pytest.raises(ValueError, match="Only one of crop, headshot_crop, or portrait_crop can be set to True"):
            EditOptions(crop=True, portrait_crop=True)

        # Test crop + headshot_crop
        with pytest.raises(ValueError, match="Only one of crop, headshot_crop, or portrait_crop can be set to True"):
            EditOptions(crop=True, headshot_crop=True)

        # Test portrait_crop + headshot_crop
        with pytest.raises(ValueError, match="Only one of crop, headshot_crop, or portrait_crop can be set to True"):
            EditOptions(portrait_crop=True, headshot_crop=True)

        # Test all three together
        with pytest.raises(ValueError, match="Only one of crop, headshot_crop, or portrait_crop can be set to True"):
            EditOptions(crop=True, portrait_crop=True, headshot_crop=True)

    def test_edit_options_straighten_mutual_exclusivity(self):
        """Test that straighten and perspective_correction are mutually exclusive."""
        with pytest.raises(ValueError, match="Only one of straighten or perspective_correction can be set to True"):
            EditOptions(straighten=True, perspective_correction=True)

    def test_edit_options_valid_combinations(self):
        """Test valid combinations of mutually exclusive options."""
        # Only crop
        options = EditOptions(crop=True, straighten=True)
        assert options.crop is True
        assert options.straighten is True

        # Only portrait_crop
        options = EditOptions(portrait_crop=True, perspective_correction=True)
        assert options.portrait_crop is True
        assert options.perspective_correction is True

        # Only headshot_crop
        options = EditOptions(headshot_crop=True, straighten=True)
        assert options.headshot_crop is True
        assert options.straighten is True

        # False values should not trigger validation
        options = EditOptions(crop=False, portrait_crop=True, straighten=False, perspective_correction=True)
        assert options.crop is False
        assert options.portrait_crop is True
        assert options.straighten is False
        assert options.perspective_correction is True

    def test_edit_options_none_values_allowed(self):
        """Test that None values don't trigger mutual exclusivity validation."""
        # None values should be allowed alongside True values
        options = EditOptions(crop=True, portrait_crop=None, headshot_crop=None)
        assert options.crop is True
        assert options.portrait_crop is None
        assert options.headshot_crop is None


class TestEnumIntegration:
    """Test enum integration in workflows."""

    @pytest.mark.parametrize(
        "photo_type,expected_value",
        [
            ("NO_TYPE", "NO_TYPE"),
            ("PORTRAITS", "PORTRAITS"),
            ("WEDDING", "WEDDING"),
            ("REAL_ESTATE", "REAL_ESTATE"),
            ("LANDSCAPE_NATURE", "LANDSCAPE_NATURE"),
            ("EVENTS", "EVENTS"),
            ("FAMILY_NEWBORN", "FAMILY_NEWBORN"),
            ("BOUDOIR", "BOUDOIR"),
            ("SPORTS", "SPORTS"),
        ],
    )
    def test_photography_type_values(self, photo_type, expected_value):
        """Test PhotographyType enum values are correct."""
        assert getattr(PhotographyType, photo_type).value == expected_value

    @pytest.mark.parametrize(
        "ratio_type,expected_value",
        [
            ("RATIO_2X3", "2X3"),
            ("RATIO_4X5", "4X5"),
            ("RATIO_5X7", "5X7"),
        ],
    )
    def test_crop_aspect_ratio_values(self, ratio_type, expected_value):
        """Test CropAspectRatio enum values are correct."""
        assert getattr(CropAspectRatio, ratio_type).value == expected_value


class TestWorkflowErrorHandling:
    """Test error handling in workflows."""

    @pytest.mark.asyncio
    async def test_quick_edit_project_creation_failure(self, mock_client_factory, sample_profiles):
        """Test quick_edit when project creation fails."""
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.side_effect = ProjectError("Project creation failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(ProjectError):
                await quick_edit(api_key="test-key", profile_key=196, image_paths=["img1.dng"])

            # Verify subsequent steps were not called
            mock_client.upload_images.assert_not_called()

    @pytest.mark.asyncio
    async def test_quick_edit_upload_failure(self, mock_client_factory, sample_profiles):
        """Test quick_edit when upload fails completely."""
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.side_effect = UploadError("Upload failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(UploadError):
                await quick_edit(api_key="test-key", profile_key=196, image_paths=["img1.dng"])

            # Verify editing was not attempted
            mock_client.start_editing.assert_not_called()

    @pytest.mark.asyncio
    async def test_quick_edit_editing_failure(self, successful_upload_summary, mock_client_factory, sample_profiles):
        """Test quick_edit when editing fails."""
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.side_effect = ProjectError("Editing failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(ProjectError):
                await quick_edit(api_key="test-key", profile_key=196, image_paths=["img1.dng"])

            # Verify download links were not requested
            mock_client.get_download_links.assert_not_called()

    @pytest.mark.asyncio
    async def test_quick_edit_export_failure(self, successful_upload_summary, mock_client_factory, sample_profiles):
        """Test quick_edit when export fails but editing succeeds."""
        download_links = ["https://download1.com"]

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = download_links
            mock_client.export_project.side_effect = ProjectError("Export failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(ProjectError, match="Export failed"):
                await quick_edit(
                    api_key="test-key",
                    profile_key=196,  # Using RAW profile key from sample_profiles
                    image_paths=["img1.dng"],  # Using RAW file to match profile
                    export=True,  # This is the key - we need to set export=True to trigger the export failure
                )

            # Verify the workflow calls up to the point of failure
            mock_client.create_project.assert_called_once()
            mock_client.upload_images.assert_called_once()
            mock_client.start_editing.assert_called_once()
            mock_client.get_download_links.assert_called_once()
            mock_client.export_project.assert_called_once_with("test-project-uuid")

            # Verify export links were not requested since export_project failed
            mock_client.get_export_links.assert_not_called()


class TestWorkflowDataFlow:
    """Test data flow through complete workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_workflow_data_integrity(self, helpers, mock_client_factory, sample_profiles):
        """Test complete workflow data integrity."""
        download_links = [
            "https://download1.com",
            "https://download2.com",
            "https://download3.com",
        ]
        export_links = ["https://export1.com"]
        successful_upload_summary = helpers.create_successful_upload_summary(file_count=3)

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = download_links
            mock_client.export_project.return_value = None
            mock_client.get_export_links.return_value = export_links
            mock_client_class.return_value = mock_client

            result = await quick_edit(
                api_key="integration-test-key",
                profile_key=29132,  # JPG profile key from sample_profiles (was 196 - RAW profile)
                image_paths=[
                    "photo1.jpg",
                    "photo2.jpg",
                    "photo3.jpg",
                ],  # JPG files match JPG profile
                project_name="Integration Test Project",
                photography_type=PhotographyType.FAMILY_NEWBORN,
                export=True,
            )

            # Verify complete data flow
            assert result.project_uuid == "test-project-uuid"
            assert result.upload_summary.total == 3
            assert result.upload_summary.successful == 3
            assert len(result.download_links) == 3
            assert len(result.export_links or []) == 1

            # Verify all calls were made with correct parameters
            mock_client.create_project.assert_called_once_with("Integration Test Project")
            mock_client.upload_images.assert_called_once_with("test-project-uuid", ["photo1.jpg", "photo2.jpg", "photo3.jpg"])
            mock_client.start_editing.assert_called_once_with(
                "test-project-uuid",
                29132,  # Updated to match JPG profile key
                PhotographyType.FAMILY_NEWBORN,
                edit_options=None,
            )
            mock_client.get_download_links.assert_called_once_with("test-project-uuid")
            mock_client.export_project.assert_called_once_with("test-project-uuid")
            mock_client.get_export_links.assert_called_once_with("test-project-uuid")

    @pytest.mark.asyncio
    async def test_workflow_parameter_passing(self, helpers, mock_client_factory, sample_profiles):
        """Test that all parameters are passed correctly through workflows."""
        successful_upload_summary = helpers.create_successful_upload_summary()

        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = ["https://download1.com"]
            mock_client_class.return_value = mock_client

            await quick_edit(api_key="test-key", profile_key=196, image_paths=["img1.dng"])


# Test scenarios with multiple parameters
class TestQuickEditScenarios:
    """Test various quick_edit usage scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "photography_type,expected_calls",
        [
            (PhotographyType.WEDDING, 1),
            (PhotographyType.PORTRAITS, 1),
            (None, 1),
        ],
    )
    async def test_quick_edit_photography_types(
        self,
        photography_type,
        expected_calls,
        successful_upload_summary,
        mock_client_factory,
        sample_profiles,
    ):
        """Test quick_edit with different photography types."""
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = ["https://download1.com"]
            mock_client_class.return_value = mock_client

            await quick_edit(
                api_key="test-key",
                profile_key=196,
                image_paths=["img1.dng"],
                photography_type=photography_type,
            )

            assert mock_client.start_editing.call_count == expected_calls
            # Verify the photography type was passed correctly
            call_args = mock_client.start_editing.call_args
            assert call_args[0][2] == photography_type  # Third argument is photography_type

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "export,expected_export_calls",
        [
            (True, 1),
            (False, 0),
        ],
    )
    async def test_quick_edit_export_scenarios(
        self,
        export,
        expected_export_calls,
        successful_upload_summary,
        mock_client_factory,
        sample_profiles,
    ):
        """Test quick_edit with and without export."""
        with patch("imagen_sdk.imagen_sdk.ImagenClient") as mock_client_class:
            mock_client = mock_client_factory()
            mock_client.get_profiles.return_value = sample_profiles
            mock_client.create_project.return_value = "test-project-uuid"
            mock_client.upload_images.return_value = successful_upload_summary
            mock_client.start_editing.return_value = None
            mock_client.get_download_links.return_value = ["https://download1.com"]
            mock_client.export_project.return_value = None
            mock_client.get_export_links.return_value = ["https://export1.com"]
            mock_client_class.return_value = mock_client

            result = await quick_edit(
                api_key="test-key",
                profile_key=196,
                image_paths=["img1.dng"],
                export=export,
            )

            assert mock_client.export_project.call_count == expected_export_calls
            assert mock_client.get_export_links.call_count == expected_export_calls

            if export:
                assert result.export_links == ["https://export1.com"]
            else:
                assert result.export_links is None


# Marks for organizing tests
pytestmark = [
    pytest.mark.workflow,  # Mark all tests in this file as workflow tests
]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
