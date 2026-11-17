import hashlib
from pathlib import Path

import pandas as pd
from backend.app.config import settings
from backend.app.db import get_session
from backend.app.models.dataset import Dataset
from backend.app.schemas.dataset import (
    ColumnMappingUpdate,
    DatasetPreviewResponse,
    DatasetResponse,
    SeriesOption,
)
from backend.app.services.data_cleaner import clean_dataset
from backend.app.services.data_profiler import detect_columns, profile_dataset
from backend.app.services.sample_data import ensure_sample_data_file
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlmodel import Session

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/sample", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_sample_dataset(session: Session = Depends(get_session)):
    """Generates realistic synthetic retail data and saves it as an active dataset."""
    sample_file = ensure_sample_data_file()
    df = pd.read_csv(sample_file)

    hasher = hashlib.sha256()
    with open(sample_file, "rb") as f:
        hasher.update(f.read())
    file_hash = hasher.hexdigest()

    detected = detect_columns(df)
    report = profile_dataset(
        df=df,
        date_col=detected["date_col"],
        target_col=detected["target_col"],
        group_cols=detected["group_cols"],
    )

    dataset = Dataset(
        name="Retail Sales (Sample - 3 Stores x 5 Products)",
        file_path=str(sample_file),
        file_hash=file_hash,
        row_count=len(df),
        col_count=len(df.columns),
        date_col=detected["date_col"],
        target_col=detected["target_col"],
        group_cols=detected["group_cols"],
        regressor_cols=detected["regressor_cols"],
        frequency=report.get("frequency", "D"),
        quality_report=report,
        audit_log=[],
    )

    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """
    Accepts CSV or Excel files up to 10 MB and 200,000 rows.
    Auto-detects columns and generates a preliminary data-quality report.
    """
    filename = file.filename or "upload.csv"
    ext = Path(filename).suffix.lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.",
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    file_hash = hashlib.sha256(content).hexdigest()
    save_filename = f"{file_hash[:12]}_{filename}"
    save_path = settings.STORAGE_DIR / "datasets" / save_filename

    with open(save_path, "wb") as f:
        f.write(content)

    try:
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(save_path)
        else:
            df = pd.read_csv(save_path)
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse uploaded file: {str(e)}",
        )

    if len(df) > settings.MAX_UPLOAD_ROWS:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset exceeds row limit of {settings.MAX_UPLOAD_ROWS:,} rows. Found {len(df):,} rows.",
        )

    detected = detect_columns(df)
    report = profile_dataset(
        df=df,
        date_col=detected["date_col"],
        target_col=detected["target_col"],
        group_cols=detected["group_cols"],
    )

    dataset = Dataset(
        name=Path(filename).stem.replace("_", " ").title(),
        file_path=str(save_path),
        file_hash=file_hash,
        row_count=len(df),
        col_count=len(df.columns),
        date_col=detected["date_col"],
        target_col=detected["target_col"],
        group_cols=detected["group_cols"],
        regressor_cols=detected["regressor_cols"],
        frequency=report.get("frequency", "D"),
        quality_report=report,
        audit_log=[],
    )

    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, session: Session = Depends(get_session)):
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found. Please upload a new dataset or use sample data.",
        )
    return dataset


@router.post("/{dataset_id}/mapping", response_model=DatasetResponse)
def update_column_mapping(
    dataset_id: str,
    mapping: ColumnMappingUpdate,
    session: Session = Depends(get_session),
):
    """Allows user to override detected column roles and re-profiles the dataset."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset file missing after restart. Please re-upload.",
        )

    df = pd.read_excel(file_path) if file_path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(file_path)

    # Validate specified columns exist in dataframe
    for col in [mapping.date_col, mapping.target_col] + mapping.group_cols + mapping.regressor_cols:
        if col and col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Column '{col}' does not exist in dataset.",
            )

    report = profile_dataset(
        df=df,
        date_col=mapping.date_col,
        target_col=mapping.target_col,
        group_cols=mapping.group_cols,
    )

    dataset.date_col = mapping.date_col
    dataset.target_col = mapping.target_col
    dataset.group_cols = mapping.group_cols
    dataset.regressor_cols = mapping.regressor_cols
    dataset.frequency = report.get("frequency", "D")
    dataset.quality_report = report

    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset(
    dataset_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=5, le=100),
    session: Session = Depends(get_session),
):
    """Returns paginated rows and schema for data inspection."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset file missing from disk. Please re-upload or click sample data.",
        )

    df = pd.read_excel(file_path) if file_path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(file_path)

    total_rows = len(df)
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)

    page_df = df.iloc[start_idx:end_idx].fillna("")
    # Convert numpy types to native Python
    records = page_df.to_dict(orient="records")
    dtypes = {c: str(df[c].dtype) for c in df.columns}

    return {
        "columns": list(df.columns),
        "dtypes": dtypes,
        "total_rows": total_rows,
        "page": page,
        "page_size": page_size,
        "rows": records,
    }


@router.get("/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str, session: Session = Depends(get_session)):
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    return dataset.quality_report


@router.post("/{dataset_id}/clean", response_model=DatasetResponse)
def apply_cleaning(dataset_id: str, session: Session = Depends(get_session)):
    """
    Executes automated data cleaning:
    - deduplicates timeline keys
    - fills missing dates
    - clips negative sales
    - imputes nulls
    - clips extreme outliers
    Records full audit log and updates dataset profile.
    """
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file missing.")

    df = pd.read_excel(file_path) if file_path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(file_path)

    cleaned_df, new_logs = clean_dataset(
        df=df,
        date_col=dataset.date_col,
        target_col=dataset.target_col,
        group_cols=dataset.group_cols,
        regressor_cols=dataset.regressor_cols,
        frequency=dataset.frequency,
    )

    # Save cleaned file back
    cleaned_df.to_csv(file_path, index=False)

    # Re-profile cleaned dataset
    new_report = profile_dataset(
        df=cleaned_df,
        date_col=dataset.date_col,
        target_col=dataset.target_col,
        group_cols=dataset.group_cols,
    )

    existing_audit = dataset.audit_log or []
    dataset.audit_log = existing_audit + new_logs
    dataset.quality_report = new_report
    dataset.row_count = len(cleaned_df)

    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


@router.get("/{dataset_id}/series", response_model=list[SeriesOption])
def get_available_series(dataset_id: str, session: Session = Depends(get_session)):
    """Lists selectable series (All combined + individual category/store/product groups)."""
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file missing.")

    df = pd.read_excel(file_path) if file_path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(file_path)

    series_options = [
        SeriesOption(
            id="all",
            name="Overall (All Series Combined)",
            row_count=len(df),
            date_start=str(df[dataset.date_col].min()) if dataset.date_col in df.columns else "",
            date_end=str(df[dataset.date_col].max()) if dataset.date_col in df.columns else "",
        )
    ]

    # If group columns exist, list top group combinations
    if dataset.group_cols:
        valid_groups = [g for g in dataset.group_cols if g in df.columns]
        if valid_groups:
            grouped = df.groupby(valid_groups).size().reset_index(name="count")
            # Limit to top 50 combinations to avoid UI overflow
            for _, row in grouped.head(50).iterrows():
                val_parts = [str(row[g]) for g in valid_groups]
                key_id = "__".join(val_parts)
                display_name = " / ".join(val_parts)
                series_options.append(
                    SeriesOption(
                        id=key_id,
                        name=display_name,
                        row_count=int(row["count"]),
                        date_start=str(df[dataset.date_col].min()),
                        date_end=str(df[dataset.date_col].max()),
                    )
                )

    return series_options


@router.get("/{dataset_id}/drift")
def get_dataset_drift(dataset_id: str, session: Session = Depends(get_session)):
    """Computes PSI and KS distribution drift report to assess data staleness."""
    from backend.app.services.ml.drift import compute_drift_report

    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file missing.")

    df = pd.read_excel(file_path) if file_path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(file_path)

    return compute_drift_report(
        df=df,
        date_col=dataset.date_col,
        target_col=dataset.target_col,
        regressor_cols=dataset.regressor_cols or [],
    )
