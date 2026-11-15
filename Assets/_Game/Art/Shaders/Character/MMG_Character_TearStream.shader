// Race3D formal (from v3b): tear stream (Blender material M_TearStream). UV u runs across the stream, v from the eye down.
// alpha = 0.85 x (v below _Flow, 0.08 soft end) x (1 - |2u - 1|^6); colour light blue in the middle, a darker blue
// outline toward the edges, a white line around u = 0.38.
Shader "MMG/Character/TearStream"
{
    Properties
    {
        _BodyColor ("Body", Color) = (0.690, 0.839, 0.980, 1)
        _EdgeColor ("Outline", Color) = (0.376, 0.588, 0.871, 1)
        _Flow ("Flow", Range(0, 1)) = 0.5
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Transparent" "Queue" = "Transparent+5" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull Off
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _BodyColor, _EdgeColor; float _Flow;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct V { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };
            V vert(A i) { V o; o.positionCS = TransformObjectToHClip(i.positionOS.xyz); o.uv = i.uv; return o; }
            float Range01(float x, float a, float b) { return saturate((x - a) / (b - a)); }
            half4 frag(V i) : SV_Target
            {
                float u = i.uv.x, v = i.uv.y;
                float reveal = 1 - Range01(v, _Flow - 0.08, _Flow);
                float ab = abs(2 * u - 1);
                float a = reveal * (1 - pow(ab, 6)) * 0.85;
                float hl = 1 - Range01(abs(u - 0.38), 0.04, 0.14);
                half3 body = lerp(_BodyColor.rgb, _EdgeColor.rgb, Range01(ab, 0.55, 0.85));
                return half4(lerp(body, 1, hl), a);
            }
            ENDHLSL
        }
    }
}
