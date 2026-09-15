# asistente-nutricional
Hola soy Lex Ortega y este es un proyecto para acreditar el primer modulo del curso: Inteligencia Artificial Aplicada con Llama.

En general los requerimentos son estos:
El reto es abierto: tu equipo elige un problema real, de su propio contexto o propuesto por el sensei, que un asistente basado en Llama pueda resolver. Algunos ejemplos válidos: un asistente que responda preguntas frecuentes usando RAG sobre un documento real, un asistente ajustado con LoRA para responder en un tono o formato específico, o un asistente que combine RAG y fine-tuning para un caso de uso más completo.


Para mi proyecto, estoy usando la opcion de un asistente que reponde usando un RAG especifico, la idea es que el sistema reciba dos archivos clave:
 - equivalencias.json: contiene una lista de alimentos y sus respectivas cantidades equivalentes a una porción
 - recetas.json: contiene varias recetas que se pueden realizar utilizando los alimentos anteriormente listados, dentro tambien se colocan las porciones correctas consideradas por cada receta

Las porciones son determinadas por un especialista, un nutriologo que asigna una dieta especifica. Esto mas adelante podria mejorarse generando tambien un agente inteligente que nos permita generar esto de acuerdo a lo que el usuario ingresara.

Esta informacion se carga a la aplicacion para posteriormente ser usada en las consultas que haga el usuario.

La funcion principal se llama pregunta y recibe como parametros de entrada principales la pregunta del usuario y el modelo que desea usar, (entre otros) este tiene uno por default asi que puede no ser enviado y aun asi funcionaria.

El front de la aplicacion se esta desplegando usando streamlit para que este disponible a quien acceda a la url, sin embargo, tambien la tengo en colab, usando gradle, aunque la interfaz es mas simple.


Requiere el uso de un token de groq que se carga en esta variable:
GROQ_API_KEY = "token..."