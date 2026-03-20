from fastapi import APIRouter, Depends, HTTPException
import uuid
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.pack_generator import generate_gtm_pack

router = APIRouter()

@router.post("/{candidate_id}", summary="Generate a GTM pack for a candidate")
async def generate_pack(candidate_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        pack = generate_gtm_pack(db, candidate_id)
        return {
            "message": f"Generation triggered successfully for candidate {candidate_id}", 
            "status": "success",
            "pack_id": pack.id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
