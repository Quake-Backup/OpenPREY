#ifndef _BSE_API_H_INC_
#define _BSE_API_H_INC_

#include "BSEInterface.h"

class idDecl;

typedef idDecl* (*BSE_AllocDeclEffect_t)(void);

rvBSEManager*				openPR06_GetIntegratedBSEManager( void );
rvDeclEffectEdit*			openPR06_GetIntegratedBSEDeclEffectEdit( void );
idDecl*						openPR06_AllocIntegratedBSEDeclEffect( void );
bool						openPR06_IsIntegratedBSEDeclEffect( const idDecl *decl );

extern BSE_AllocDeclEffect_t	bseAllocDeclEffect;

#endif // _BSE_API_H_INC_
