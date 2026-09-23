PORTNAME=	renasync-gui
DISTVERSION=	0.0.1
CATEGORIES=	multimedia

MAINTAINER=	ichigo
COMMENT=	Lightweight GUI addon for Renasync
WWW=		https://codeberg.org/<your-account>/renasync-gui

LICENSE=	BSD0CLAUSE

LIB_DEPENDS=	libmpv.so:multimedia/mpv
BUILD_DEPENDS=	${PYTHON_PKGNAMEPREFIX}setuptools>=0:devel/py-setuptools@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}wheel>=0:devel/py-wheel@${PY_FLAVOR}

RUN_DEPENDS=	renasync>=0:multimedia/renasync \
		${PYTHON_PKGNAMEPREFIX}tkinter>=0:x11-toolkits/py-tkinter@${PY_FLAVOR}

USES=		python:3.10+
USE_PYTHON=	autoplist pep517

# point this at your hosted copy of the repository once it is published
MASTER_SITES=	https://codeberg.org/<your-account>/renasync-gui/archive/
DISTFILES=	0.0.1.tar.gz
WRKSRC=		${WRKDIR}/renasync-gui

post-patch:
	${REINPLACE_CMD} -e '/^license-files/d' ${WRKSRC}/pyproject.toml

.include <bsd.port.mk>