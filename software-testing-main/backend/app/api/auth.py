from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core import security
from app.core.config import settings
from app.models.models import User
from app.schemas.schemas import Token

router = APIRouter()

@router.post("/token", response_model=Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/bootstrap")
def bootstrap_db(db: Session = Depends(get_db)):
    try:
        from app.models.models import Target, CommandConfig
        import json
        
        # User
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(username="admin", password_hash=security.get_password_hash("secret"), role="admin")
            db.add(user)
            
        # Target
        t = db.query(Target).filter_by(id=1).first()
        if not t:
            t = Target(id=1, name="Localhost", host="127.0.0.1", description="Test")
            db.add(t)

        # Command
        c = db.query(CommandConfig).filter_by(id=1).first()
        if not c:
            c = CommandConfig(
                id=1,
                name="MockNmap",
                executable="python",
                allowed_args=json.dumps(["-u", "-c", "print('hello from mock'); import time; time.sleep(0.5); print('done')"]),
                timeout_seconds=5,
                regex_rules="{}"
            )
            db.add(c)
            
        db.commit()
        return {"status": "Database successfully bootstrapped!"}
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
