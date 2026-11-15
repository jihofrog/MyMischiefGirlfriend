// Race3D formal (from v3b): copy of MMG/Character/EyeBall plus the Surprise sparkle layer (_SparkleTex alpha in the eye
// texture space mixed to white by _Sparkle before the shading, as the Blender node "Sparkle"). Iris scale and pitch come
// in through _Proj from the driver.
// Eyeball (_Mode 1): socket AO from the
// texture alpha read through UV0 (stays with the lids when the gaze turns), white dimmed by _ViewDim and highlights by a
// further _HLDim as the view turns away from the face front (object +Z = Blender -y); the front view is unchanged. Painted eye textures with a soft toon
// light response (same sun as the skin).
// _Mode 0: UV0 texture (lash band, A / v5g iris), 1: eyeball - r30 eye front projected from object space and turned about
// the vertical axis by _GazeYaw (radians, + = character left), 2: flat _BaseColor. _Clip: alpha cut at 0.5.
// Object space of the FBX (bake_space_transform): Blender x = -X, y = -Z, z = Y.
Shader "MMG/Character/EyeBallSparkle"
{
    Properties
    {
        _BaseMap ("Texture", 2D) = "white" {}
        _BaseColor ("Colour", Color) = (1, 1, 1, 1)
        _Mode ("Mode (0 uv, 1 eyeball, 2 flat)", Float) = 0
        _Clip ("Alpha clip (0/1)", Float) = 0
        _A2C ("Alpha to coverage (0/1)", Float) = 0
        _UseAO ("Eyeball socket AO from alpha (0/1)", Float) = 0
        _ViewDim ("Dim at side views", Range(0, 0.5)) = 0.10
        _HLDim ("Extra highlight dim at side views", Range(0, 0.5)) = 0.20
        _LitLo ("Light low", Range(0, 1)) = 0.8
        _LitMid ("Light mid", Range(0, 1)) = 0.93
        _LightDir ("Light direction (world)", Vector) = (-0.3, 0.8, -0.5, 0)
        _GazeYaw ("Gaze yaw (rad)", Float) = 0
        _Proj ("Eyeball projection (su, tu, sv, tv)", Vector) = (1, 0, 1, 0)
        _SparkleTex ("Sparkle (eye texture space)", 2D) = "black" {}
        _Sparkle ("Sparkle", Range(0, 1)) = 0
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            AlphaToMask [_A2C]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap); TEXTURE2D(_SparkleTex); SAMPLER(sampler_SparkleTex);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST; half4 _BaseColor; float _Mode, _Clip, _A2C, _UseAO, _ViewDim, _HLDim, _LitLo, _LitMid, _GazeYaw, _Sparkle; float4 _LightDir, _Proj;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct V { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 normalWS : TEXCOORD1; float3 posOS : TEXCOORD2; float3 posWS : TEXCOORD3; };
            V vert(A i)
            {
                V o;
                o.positionCS = TransformObjectToHClip(i.positionOS.xyz);
                o.uv = i.uv; o.normalWS = TransformObjectToWorldNormal(i.normalOS); o.posOS = i.positionOS.xyz; o.posWS = TransformObjectToWorld(i.positionOS.xyz);
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                float2 uv = i.uv;
                if (_Mode > 0.5 && _Mode < 1.5)
                {
                    float3 b = float3(-i.posOS.x, -i.posOS.z, i.posOS.y);
                    float a = -_GazeYaw, c = cos(a), s = sin(a);
                    uv = float2((b.x * c - b.y * s) * _Proj.x + _Proj.y, b.z * _Proj.z + _Proj.w);
                }
                half4 t = _Mode > 1.5 ? _BaseColor : SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv) * _BaseColor;
                if (_Mode > 0.5 && _Mode < 1.5) t.rgb = lerp(t.rgb, 1, SAMPLE_TEXTURE2D(_SparkleTex, sampler_SparkleTex, uv).a * _Sparkle);
                if (_Clip > 0.5 && _A2C < 0.5) clip(t.a - 0.5);
                if (_A2C > 0.5) clip(t.a - 0.02);
                float l = saturate(dot(normalize(i.normalWS), normalize(_LightDir.xyz)));
                float lit = l < 0.45 ? lerp(_LitLo, _LitMid, smoothstep(0.15, 0.45, l)) : lerp(_LitMid, 1.0, smoothstep(0.45, 0.75, l));
                float3 rgb = t.rgb * lit;
                if (_UseAO > 0.5 && _Mode > 0.5 && _Mode < 1.5)
                {
                    float ao = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).a;
                    float f = dot(normalize(GetWorldSpaceViewDir(i.posWS)), normalize(TransformObjectToWorldDir(float3(0, 0, 1))));
                    float s = smoothstep(0.55, 1.0, f);
                    float hl = smoothstep(0.93, 0.99, dot(t.rgb, float3(0.2126, 0.7152, 0.0722)));
                    rgb *= ao * lerp(1.0 - _ViewDim, 1.0, s) * (1.0 - _HLDim * hl * (1.0 - s));
                    return half4(rgb, 1);
                }
                return half4(rgb, _A2C > 0.5 ? t.a : 1);
            }
            ENDHLSL
        }
    }
}
